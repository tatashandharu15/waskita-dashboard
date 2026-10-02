# Deploy Waskita Analytics ke Vercel (Nyaman & Production Ready)

## 🚨 Repository Research (Batasan Vercel Yang PENTING)
Vercel berbasis **Serverless Functions** (AWS Lambda under the hood) dengan batasan:
- **Read-only filesystem** kecuali folder `/tmp` dan `assets/` yang di-bundle saat build-time
- **Timeout maks**: Hobby 10s, Pro 60s — parsing Excel 2000+ rows pakai Pandas aman di 10s
- **Stateless**: Tiap invocation = cold start baru. **Semua data (uploads xlsx, parsed JSON, SQLite .db) TIDAK AKAN PERSIST** antar invocation tanpa external storage

Ada **dua jalur deploy** sesuai kenyamanan:

---

### 🅰️ Opsi A — "Super Nyaman Zero Config" (Rekomendasi AWAL)
- **Deploy tanpa Supabase/eksternal apapun** — uploads + parsed JSON + SQLite **simpan 100% in-memory ke dalam file bundle di PARSED_DIR yang di-include di repo**
- **Cocok untuk demo / laporan internal** yang hanya butuh upload beberapa report permanent, atau dashboard showcase untuk klien tanpa sering upload ulang
- **Cara kerja persistent tanpa Supabase**: File .db + .xlsx + .json **disimpan langsung di dalam repo** (`assets/` yang ikut di-bundle saat Vercel build). New upload via admin di Vercel cuma bertahan di `/tmp` (per 1 invocation saja) — jadi **workflow**: upload local dev → auto copy ke `assets/` bundled → deploy ulang → semua production instance dapat data yang SAMA.
- **Storage fallback**: runtime invocation cek: jika ada file di `/tmp/vercel_data/` pakai itu (untuk testing upload admin di prod 1 sesi), tapi default selalu load dari `assets/` (data persistent utama).

---

### 🅱️ Opsi B — "Production Full Admin Upload Persistent" (Rekomendasi jika sering upload)
- **Tambah Supabase (Postgres + Storage S3)**: Supabase free tier cukup untuk project ini (500MB DB + 1GB storage)
- **Arsitektur Vercel friendly**: 
  - Metadata uploads (rows_count, dates, is_active, hash, filename) → **Simpan di Supabase Postgres**
  - File .xlsx original + parsed.json → **Simpan di Supabase Storage S3**
  - SQLite lokal di /tmp hanya sebagai fallback cache 1 invocation, Supabase = source of truth
- **Harga**: Supabase free tier SELALU ada untuk project kecil, tanpa CC awal
- **Admin upload works 100% persistent di Vercel tanpa redeploy**

---

## Rekomendasi Saya: **Opsi A DULU** (Nyaman, cepat, zero account eksternal untuk demo)

## Files and Modules yang Akan Diubah
- `app/config.py`: Update `UPLOAD_DIR`, `PARSED_DIR`, `DB_PATH` → ENV override, auto fallback ke `assets/` jika Vercel (detect `VERCEL` env). Default load persistent data dari `assets/` directory (yang akan saya buat + copy current sample Kapolri ke sini). Runtime upload di Vercel pakai `/tmp/vercel_data` (best-effort saja)
- `app/db.py`: Buat `BUNDLED_ASSETS_DIR = BASE_DIR.parent / "assets"`; `get_active()` cek: jika Vercel + record di DB tidak ada → fallback cari `assets/*.json` yang di-bundle + inject record "virtual" persistent
- `assets/` (NEW): Directory persistent untuk bundling Vercel — copy `dashboard.db`, current parsed Kapolri `.json`, dan optionally original sample xlsx — .gitinclude agar ikut commit. Isi otomatis di-generate dari current state local yang sudah verified 2193 rows.
- `api/index.py` (NEW): **Vercel Entry Point** using Mangum adapter. `from main import app; handler = Mangum(app, lifespan="off")` — karena Vercel serverless Python tidak support lifespan async (workaround: disable lifespan, auto init_db repo di `MangumAdapter.pre_run` atau per-request lazy init jika `app.state.repo` belum ada).
- `requirements.txt`: Tambah `mangum>=0.17.0` (official FastAPI → AWS Lambda adapter yang dipakai Vercel Python runtime)
- `vercel.json` (NEW): Vercel config — `{ "buildCommand": "cp -r uploads/feab*.xlsx assets/ 2>/dev/null; cp -r data_parsed/*.json assets/ 2>/dev/null; cp dashboard.db assets/ 2>/dev/null; true", "installCommand": "pip install -r requirements.txt", "functions": { "api/index.py": { "maxDuration": 60 } }, "rewrites": [{ "source": "/(.*)", "destination": "/api/index" }] }` + `regions: "sin1"` (Singapore, dekat Indonesia, latency rendah = paling nyaman buat user Indo)
- `.gitignore`: Un-ignore `assets/*.db`, `assets/*.json`, `assets/*.xlsx` (opsi A butuh data ikut di-bundle)

## Implementation Steps (Dependency Order)

### Step 1: Siapkan `assets/` directory persistent Vercel
- Buat folder `/Users/tatas/Downloads/SiberIndo/dashboard-analitic/assets`
- Copy sample yang sudah verified:
  - `uploads/feab74a5-483c-4229-8fdf-d8f6f5940d61.xlsx` → `assets/kapolri-sample.xlsx`
  - `data_parsed/feab74a5-483c-4229-8fdf-d8f6f5940d61.json` → `assets/kapolri-sample.json`
  - `dashboard.db` → `assets/dashboard.db` (current state dengan active record)
- Bikin file empty `assets/.gitkeep` untuk jaga-jaga

### Step 2: Update `app/config.py` Vercel-aware paths
- Tambah deteksi env `IS_VERCEL = bool(os.getenv('VERCEL'))`
- Jika `IS_VERCEL`:
  - `UPLOAD_DIR = Path(os.getenv('UPLOAD_DIR', '/tmp/vercel_data/uploads'))`
  - `PARSED_DIR = Path(os.getenv('PARSED_DIR', '/tmp/vercel_data/data_parsed'))`
  - `DB_PATH = Path(os.getenv('DB_PATH', BASE_DIR.parent / 'assets' / 'dashboard.db'))` → Vercel **read-only** tapi SQLite cuma perlu SELECT, data active akan di-load via fallback mechanism jika DB read-only (workaround: inject record virtual dari assets JSON)
- Penting: tambah env `SAMPLE_BUNDLED_JSON` jika mau point ke file bundled lain
- Jangan `mkdir` di `assets/` (read-only Vercel), cuma mkdir untuk /tmp path

### Step 3: Update `app/db.py` Fallback Bundled Assets (Opsi A Persistent Workaround)
- Tambah `ASSETS_DIR = BASE_DIR.parent / "assets"` global constant
- Modifikasi `get_active()`: sebelum return None (tidak ada active di DB), lakukan fallback: cek scan `ASSETS_DIR.glob('*.json')` — ambil file JSON terbaru (atau `SAMPLE_BUNDLED_JSON` env), parse metadata, build `UploadRecord` virtual in-memory (id=9999, is_active=1, filename_stored + parsed_json_path point ke ASSETS_DIR path absolute), tanpa INSERT ke DB karena read-only. Return record ini SEBAGAI active upload.
- Modifikasi `load_parsed_json(upload_id)`: jika upload_id == 9999 → load dari assets JSON, jika lain → coba DB path terlebih dahulu, fallback assets.
- Workaround SQLite read-only Vercel: set env `SQLITE_ACCESS=read_only` saat di Vercel, di `_conn()` bikin connection dengan `uri=True` + `mode=ro` (read-only) agar tidak crash saat Vercel cannot write journal WAL.

### Step 4: Update `main.py` Workaround Lifespan + Lazy Repo Init (Vercel Serverless)
- Vercel Python Lambda (`Mangum`) TIDAK support async `lifespan` yang menjalankan `print()` banner long atau init state global tahan lama
- Solusi:
  - Jika `os.getenv('VERCEL')`: buat `app = FastAPI(docs_url=None, redoc_url=None)` TANPA lifespan
  - Ganti `get_repo(request)` pattern: periksa jika `not hasattr(request.app.state, 'repo')` → create repo `UploadRepository()` baru tiap cold start (saja 10ms overhead) + set ke `app.state.repo`. Atau selalu instansiasi per-request. Untuk Opsi A (read-only assets) ini no problem, karena UploadRepository.init_db() cuma CREATE TABLE IF NOT EXISTS yang pada Vercel di-skip otomatis karena db read-only.

### Step 5: Create `api/index.py` + `vercel.json` + Update `requirements.txt`
- `api/index.py`: Import Mangum, baca app dari main, **di-wrap dengan conditional `if os.getenv('VERCEL'): disable lifespan banner**
- `vercel.json`:
  - `framework = null` (manual Python)
  - `buildCommand`: shell yang (1) ensure `assets/` ada (2) pip install requirements (done by installCommand), build nothing else
  - `installCommand = pip install -r requirements.txt`
  - `functions.api/index.py.maxDuration = 60` (Pro) atau default — upload parsing Excel 2000 rows butuh ~4-8 detik
  - `regions = ["sin1"]` (Singapore, paling dekat Indonesia — latency <50ms Jakarta)
  - `rewrites`: catch-all `/` → `/api/index`
  - `env.build.ADMIN_SECRET` di-setting nanti di Vercel UI project settings atau via `vercel env add ADMIN_SECRET` CLI
- `requirements.txt`: Tambah `mangum>=0.17.0` (satu-satunya dependency baru yang diperlukan)

### Step 6: Deployment Workflow (Paling Nyaman untuk User)
Dua pilihan cara deploy:
1. **Click Deploy via Vercel UI (PALING NYAMAN, TIDAK PERNAH SENTUH TERMINAL)**:
   - Push project ini ke GitHub/GitLab/Bitbucket private repo
   - Login [vercel.com](https://vercel.com) → Add New → Project → Import repo itu
   - Build Command dikosongkan atau default (karena sudah ada vercel.json)
   - Install Command: `pip install -r requirements.txt` (auto detect)
   - Framework Preset: `Other` (NOT Django/Flask — manual)
   - Environment Variables: Tambah `ADMIN_SECRET` = nilai rahasia permanen (contoh: `waskita-2026-rahasia-abc123xyz`) → **Important klik Add**
   - Klik Deploy. Tunggu ~2-3 menit build (pip install pandas lama) → Dapat URL production: `https://waskita-analytics-username.vercel.app`
2. **Deploy via Vercel CLI (lebih cepat untuk iteration)**: `npm i -g vercel; cd project; vercel; vercel env add ADMIN_SECRET; vercel --prod`

## Dependencies and Considerations
- **Mangum**: v0.17.0 sudah support FastAPI 0.110+, Starlette 0.36+, Python 3.12 — compatible
- **Build time Vercel**: Pandas + numpy + openpyxl total ~250MB wheel install, build + cold start pertama mungkin 3-5 detik. Subsequent calls = warm start <300ms.
- **SQLite read-only on Vercel fs**: Karena assets/ read-only → INSERT/UPDATE/DELETE (admin upload, set_active, delete, reparse) TIDAK AKAN PERSIST di Opsi A. **Ini sengaja** untuk Opsi A = showcase static dashboard dengan data sample pre-loaded. Jika user butuh admin upload persistent di production → **Upgrade ke Opsi B (Supabase)** nanti tinggal tambah repository pattern baru tanpa rubah layer API.
- **ADMIN_SECRET**: WAJIB di-set ENV di Vercel UI — jika tidak set, tiap cold start generate random baru → URL admin berubah terus (tidak nyaman). Kita warnai di step 6.
- **Region sin1 Singapore**: Default Vercel kadang pilih iad1 (US) yang latency 200ms+ dari Indonesia. Override wajib di vercel.json ke `sin1` agar cepat untuk user Indonesia.
- **Opsi A data update workflow**: Jika mau update data dashboard tanpa Supabase: Upload file Excel di local dev (uvicorn running) → auto simpan ke uploads/data_parsed/db → copy 3 file ke `assets/` → git push → Vercel auto redeploy → production update. Simple (tanpa install apapun baru) tapi butuh push git untuk update data — **cocok untuk laporan bulanan/mingguan**.

## Validation (Setelah Implement)
1. **Local test dulu sebelum push**: `uvicorn main:app --port 8000` → set `VERCEL=1 ADMIN_SECRET=test` env variable, buka `/` → dashboard data Kapolri 2193 rows muncul (active record dari assets fallback works)
2. **Test api/dashboard/active**: curl `/api/dashboard/active` → `ok:true` + `rows_count=2193`
3. **Test dark toggle di production preview URL**: Click toggle → localStorage persist dark/light
4. **Test admin URL**: `/admin/<ADMIN_SECRET>` → upload form muncul 404 jika secret salah
5. **Vercel production URL verify**: Header `x-vercel-id` ada, region sin1 Singapore latency <70ms
6. **Vercel build log tidak ada error**: Tidak ada error "cannot write readonly" di build log atau runtime function logs

## Risks dan Handling
- ❌ **Risiko 1: Opsi A admin upload tidak persistent di Vercel** → Handling: Warn user jelas di plan ini. Beri warning toast di admin upload page Opsi A: "Mode Vercel bundled: Upload baru hanya tersedia di invocation ini, untuk persistent silakan upgrade ke Supabase atau upload local + redeploy". Atau lebih baik: **Admin Upload page disabled total di production Opsi A** (kirim message: "Dashboard preview mode, untuk upload hubungi admin") dengan environment flag `VERCEL_MODE=bundle_preview`.
- ❌ **Risiko 2: Timeout parsing Excel 200k rows di Vercel** → Handling: maxDuration set 60 di vercel.json. Jika dataset > 100MB, sarankan upgrade Vercel Pro atau parse di local, copy ke assets/.
- ❌ **Risiko 3: ADMIN_SECRET lupa di-set → URL berubah terus** → Handling: Kita tambah fallback check di `main.py` banner + warning toast di admin page jika `GENERATED_SECRET_ON_STARTUP=true` dengan text merah "WARNING: ADMIN_SECRET environment tidak di-set — URL admin berubah tiap restart. Silakan set ENV ADMIN_SECRET."
- ❌ **Risiko 4: Cold start Lambat 3-5s (pandas import)** → Handling: Ini normal untuk Python serverless. Mitigation: Vercel punya fitur "Proactive Warmup" di Pro plan, atau accept 3s cold start pertama/hari.
- ❌ **Risiko 5: SQLite corrupt write di Vercel readonly fs** → Handling: Read-only mode URI `sqlite:///file:path?mode=ro` mencegah write attempt WAL/SQLITE_LOCKED. Kita pakai pattern fallback assets, sehingga tidak ada write operation di Vercel invocation Opsi A sama sekali (SELECT only).

---

## Catatan Upgrade Masa Depan ke Opsi B (nanti jika perlu)
- Tinggal ganti 1 file `app/db.py` class `UploadRepository` → implementasi `SupabaseUploadRepository` dengan:
  - `supabase-py>=2.0` dependency
  - Postgres table `uploads` schema identical to SQLite
  - Supabase Storage bucket `uploads/` untuk file xlsx + json
- `vercel.json` + `api/index.py` TIDAK PERLU DIUBAH (100% reusable)
- Rubah `from app.db import UploadRepository` → `from app.db_supabase import SupabaseUploadRepository as UploadRepository`
- Done! Admin upload persistent 100% Vercel production tanpa redeploy
