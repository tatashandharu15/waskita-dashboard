# Brand Mention Analytics Dashboard - Implementation Plan

## Task 1: Setup Skeleton Proyek & Konfigurasi Dasar
- **Status**: `pending`
- **Priority**: high
- **Depends On**: None
- **Description**:
  - Buat struktur direktori: `app/`, `app/static/` (css, js, icons), `app/templates/`, `uploads/`, `data_parsed/`, `.trae/specs/brand-mention-dashboard/` (sudah ada)
  - Buat `requirements.txt` dengan dependencies: fastapi, uvicorn[standard], pandas, openpyxl, python-multipart, jinja2
  - Buat `main.py` (entry point FastAPI): mount static files, mount templates Jinja2, inisialisasi DB di startup, log default admin secret ke console jika ENV tidak diset
  - Buat modul `app/config.py`: baca ENV `ADMIN_SECRET`, `UPLOAD_DIR`, `PARSED_DIR`, `DB_PATH`, `MAX_UPLOAD_MB`
  - Buat modul `app/db.py`: SQLite schema tabel `uploads` (id, filename_original, filename_stored, file_hash, rows_count, min_date, max_date, uploaded_at, is_active, summary_json, parsed_json_path). Fungsi init_db() buat tabel jika belum ada.
  - Tambah `.gitignore` umum (venv, __pycache__, *.pyc, .env, uploads/*, data_parsed/*, *.db)
- **Acceptance Criteria Addressed**: AC-3 (config secret), NFR-3 (zero-config startup)
- **Test Requirements**:
  - `rule` TR-1.1: Jalankan `uvicorn main:app` tanpa setup ENV apa pun → (a) server jalan port 8000, (b) SQLite file `dashboard.db` terbuat otomatis, (c) folder `uploads/` dan `data_parsed/` dibuat jika belum ada, (d) console menampilkan log URL admin secret auto-generate (e.g., "Admin URL: http://localhost:8000/admin/<random32chars>"). Evidence: terminal log startup + ls direktori
  - `rule` TR-1.2: SET `ADMIN_SECRET=test123` via ENV, restart server → log startup menampilkan admin path `/admin/test123`. Access `/admin/test123` return 200 (template empty sementara), `/admin/wrong` return 404 (bukan 403, sembunyikan existence). Evidence: curl kedua URL.
  - `rubric` TR-1.3: Kebersihan struktur direktori dan modul separation. Scale 1-5 (1=semua di satu file main.py, 3=modul config/db terpisah tapi main.py masih >500 baris, 5=jelas app/config.py, app/db.py, app/parser.py, app/api.py, main.py tipis hanya entrypoint). Threshold >=4. Evidence: file line count dan import graph.
- **Notes**: Minimal templating dulu, hanya pastikan konfigurasi dan DB siap.

## Task 2: Core Parser Excel + Engine Aggregasi Analytics (Siapkan Otak Aplikasi)
- **Status**: `pending`
- **Priority**: high
- **Depends On**: Task 1 (struktur direktori + config)
- **Description**:
  - Buat `app/parser.py` dengan fungsi utama `parse_excel_file(file_path: Path) -> ParsedResult`
  - Step parsing:
    1. Baca Excel `pd.read_excel(sheet_name=0)`
    2. Kolom cleaning: strip spasi nama kolom, handle missing kolom critical (raise ParseError deskriptif jika SOURCE/DATE/SENTIMEN/TRACKED KEYWORD/PERFORMANCE tidak ada)
    3. Konversi DATE ke datetime `pd.to_datetime(df['DATE'].replace(' ', NaN), errors='coerce')`
    4. Numeric cleaning: helper `to_numeric_safe(series)` untuk kolom: SOCIAL MEDIA INTERACTIONS, REACH, VISITS, PERFORMANCE, FOLLOWING, LIKES, SHARES, COMMENTS, VIEWS, FAVOURITES
    5. String cleaning: kolom EMOTION/COUNTRY/LANGUAGE/SOURCE ganti ''/' ' → 'Unknown'
    6. Hashtag extract: regex `#(\w+)` dari TEXT + TITLE → Counter top 50
    7. Term frequency sederhana untuk terms penting (nama, institusi) - opsional tapi bagus untuk section "Istilah Populer"
  - Step aggregasi (semua jadi dict siap JSON):
    A. metadata: rows_count, columns_count, min_date, max_date, date_range_hours, upload_date (dari waktu sekarang)
    B. overview_kpi: total_mentions, total_reach_valid, total_reach_sum, avg_reach, pct_positive, pct_neutral, pct_negative, sentiment_composite (skor -1 sd 1: (pos-neg)/total)
    C. source_distribution: list [{name, count, percentage}]
    D. keyword_distribution: list [{name, count, percentage, sentiment_pct:{pos,neu,neg}}] (cross-tab tracked_keyword vs sentiment)
    E. sentiment_distribution: {neutral:{count,pct}, positive:{...}, negative:{...}}
    F. emotion_distribution: list [{name, count, percentage}] (Unknown + emosi lain)
    G. hourly_trend: list [{hour: 0-23, count}] untuk tanggal data yang dominan (mode tanggal DATE_CLEAN) + peak_hour & peak_count
    H. top_hashtags: list [{tag, count, percentage}] top 20
    I. performance_distribution: scores_1_to_10 list count + mean/median/std + top_performers_per_source: [{source, count_10, pct_10_from_source}]
    J. engagement: [{metric: 'LIKES', total, avg, max, n_valid}, ...] untuk 8 metrik engagement
    K. language_distribution: top 10 [{lang, count, pct}]
    L. country_distribution: top 10 [{country, count, pct}]
    M. top_authors: top 15 [{author_name, author_username, count}] filter author != ' '
    N. demographics: {male_avg_pct, female_avg_pct, n_samples} dihitung dari source site/news yang punya data
    O. sentiment_per_source: [{source, pos_pct, neu_pct, neg_pct, total}]
    P. negative_sample: list 5 posts [{source, text_preview_200chars, emotion, tracked_keyword}] (hanya SENTIMEN='negative')
  - Return objek dengan semua aggregasi + path penyimpanan JSON. Simpan ke `data_parsed/<upload_id>.json` saat task 3 berjalan.
- **Acceptance Criteria Addressed**: AC-1 (parsing + JSON), AC-6 (robust parsing), FR-24 s/d FR-27
- **Test Requirements**:
  - `rule` TR-2.1: Parse file sample `data/kapolri - Mentions_Report - 2026-10-01.xlsx` dengan parser. Verifikasi: (a) rows_count = 2193, (b) hourly entries antara jam 0 sd 13 tidak ada yang >717 (jam 10 puncak), (c) total pos+neu+neg = 2193, (d) source instagram count 822, facebook 549, (e) tracked_keyword suyudi+kapolri+kepala bnn = 2193. Evidence: print field kunci dari hasil dict.
  - `rule` TR-2.2: Parser diuji dengan file xlsx "rusak ringan": (a) semua kolom EMOTION diisi ' ' (spasi) → parser ubah ke 'Unknown' dan emotion_distribution berisi 100% Unknown tanpa error, (b) kolom LIKES 50% string kosong → to_numeric_safe menghasilkan NaN tapi engagement["LIKES"]["n_valid"] = 50% rows. Evidence: print hasil parsing.
  - `rule` TR-2.3: Parser throw ParseError (message deskriptif: "Missing required columns: [SOURCE, SENTIMEN]") jika file xlsx tidak memiliki kolom krusial. Evidence: try/except dan message output.
  - `rubric` TR-2.4: Kelengkapan aggregasi (20 area insight). Scale 1-5 (1=hanya 5 area, 3=12 area, 5=semua A s/d P lengkap). Threshold >=4. Evidence: jumlah keys di dict hasil vs daftar A-P.

## Task 3: Storage Layer SQLite CRUD Uploads
- **Status**: `pending`
- **Priority**: high
- **Depends On**: Task 2 (output parser jelas), Task 1 (db.py schema)
- **Description**:
  - Perluas `app/db.py` dengan Repository pattern (kelas `UploadRepository`) atau fungsi modul-level:
    1. `create_upload(filename_original, file_hash, rows_count, min_date, max_date, parsed_dict) -> UploadRecord`: (a) Simpan file Excel dari temp ke `uploads/<uuid>.xlsx` dengan nama acak (bukan nama asli, hindari path traversal), (b) Tulis `data_parsed/<uuid>.json` dump dari parsed_dict, (c) INSERT tabel uploads kolom sesuai. (d) OTOMATIS set kolom is_active=1 untuk record baru, dan yang lain is_active=0 (hanya boleh satu aktif). (e) Cek dulu idempotensi: jika ada record dengan file_hash sama → return record existing TANPA insert baru (tetap set aktif).
    2. `list_uploads(limit=50) -> list[UploadRecord]`: ORDER BY uploaded_at DESC
    3. `get_active() -> Optional[UploadRecord]`: WHERE is_active = 1. Jika tidak ada, return None.
    4. `get_by_id(upload_id) -> Optional[UploadRecord]`
    5. `set_active(upload_id) -> bool`: SET semua is_active=0 lalu WHERE id=upload_id SET is_active=1. Return True jika berubah.
    6. `delete_upload(upload_id) -> bool`: Hapus row DB, lalu HAPUS file di uploads/<stored_name>.xlsx dan data_parsed/<upload_id>.json jika ada.
    7. `reparse_upload(upload_id, parser_func) -> UploadRecord`: Baca file xlsx original dari uploads/, jalankan parser_func lagi, overwrite file JSON data_parsed, update rows_count/min_date/max_date/summary_json di DB.
  - Definisikan dataclass `UploadRecord` atau Pydantic model untuk response API.
- **Acceptance Criteria Addressed**: AC-1 (auto set aktif), AC-5 (set-active + otomatis baru), AC-9 (list/delete/set-active)
- **Test Requirements**:
  - `rule` TR-3.1: Urutan operasi: (1) create_upload A, (2) create_upload B → cek DB: hanya B yang is_active=1. (3) set_active(A) → hanya A is_active=1. (4) list_uploads → 2 record, urutan B lalu A (DESC). (5) delete_upload(B) → DB hanya 1 record (A), file uploads/ B.xlsx dan B.json hilang dari disk. Evidence: (a) sqlite3 CLI query SELECT id,is_active,filename, (b) ls uploads data_parsed sebelum/sesudah delete.
  - `rule` TR-3.2: Idempotency: create_upload FILE_SAMA (hash md5 sama) dipanggil 2x → count DB uploads cuma bertambah 1, file cuma 1 di uploads. Evidence: md5sum file + count DB.
  - `rule` TR-3.3: Reparse upload A yang ada: (1) edit file JSON di data_parsed/A.json dengan nilai dummy (total=999), (2) panggil reparse_upload(A, parser), (3) baca kembali JSON dan record A → total rows kembali ke 2193. Evidence: diff JSON before/after reparse.

## Task 4: Backend API Endpoints (Public + Admin)
- **Status**: `pending`
- **Priority**: high
- **Depends On**: Task 3 (storage siap)
- **Description**:
  - Buat `app/api.py` atau mount langsung di `main.py` dengan APIRouter:
    - **Admin Mount (prefix `/admin/{secret}`)**: middleware check secret sebelum mount semua route di bawahnya. Jika secret salah, raise HTTPException 404 (bukan 401/403) agar tidak membocorkan URL.
    - A. **Public Routes**:
      1. `GET /` → render Jinja2 template `public/dashboard.html` (halaman dashboard utama)
      2. `GET /api/dashboard/active` → JSON. Jika ada aktif: `{"ok": true, "upload_id": id, "upload_meta": {...summary...}, "analytics": parsed_dict_lengkap}`. Jika tidak ada aktif: `{"ok": false, "message": "No active report", "admin_url": config.admin_path}` (hanya informatif, tidak bocor secret jika tidak tahu).
    - B. **Admin Routes**:
      3. `GET /admin/{secret}` → render Jinja2 `admin/upload.html` (halaman admin: upload form + list history)
      4. `POST /admin/{secret}/upload` → multipart/form-data field `file`. (a) cek extension: hanya .xlsx/.xls, (b) cek size: < MAX_UPLOAD_MB, (c) simpan ke temp file, hash md5, (d) panggil parser.parse_excel_file → jika gagal raise 400 ParseError, (e) repository.create_upload() → return `{"ok": true, "upload": upload_meta_dict}`
      5. `GET /admin/{secret}/api/uploads` → list_uploads JSON `{"uploads": [..]}` untuk halaman admin refresh history
      6. `POST /admin/{secret}/api/uploads/{id}/set-active` → set_active(id). return {"ok": true, "now_active_id": id}
      7. `DELETE /admin/{secret}/api/uploads/{id}` → delete_upload(id). return {"ok": true}
      8. `POST /admin/{secret}/api/uploads/{id}/reparse` → reparse_upload. return {"ok": true, "upload": upload_meta}
  - Semua error route admin secret SALAH → 404. CORS: set default allow all (karena publik + internal). Error handler untuk ParseError → 400 JSON deskriptif.
- **Acceptance Criteria Addressed**: AC-1 (POST upload → aktif), AC-3 (URL secret 404 if wrong), FR-28 s/d FR-33, AC-5, AC-9
- **Test Requirements**:
  - `rule` TR-4.1: Semua endpoint berjalan via curl. ADMIN=testsecret yang diset ENV. (1) `curl -X POST -F "file=@data/kapolri.xlsx" http://localhost:8000/admin/${ADMIN}/upload` → return ok:true dan upload_meta. (2) `curl http://localhost:8000/api/dashboard/active | jq .upload_id` → return ID upload baru. (3) `curl -X POST http://localhost:8000/admin/${ADMIN}/api/uploads/1/set-active` (4) `curl -X DELETE .../uploads/2` → ok:true. Semua status code: upload=2xx, dashboard active=200 atau 2xx. Evidence: curl commands output + status codes.
  - `rule` TR-4.2: Secret protection: `curl http://localhost:8000/admin/WRONGSECRET` = 404 status code. `curl -X POST http://localhost:8000/admin/WRONGSECRET/upload` = 404 (tidak bisa upload tanpa secret benar). `curl http://localhost:8000/admin/${ADMIN}/api/uploads` = 200 JSON list. Evidence: curl -I output headers.
  - `rule` TR-4.3: Error handling upload file invalid: (a) upload file.txt rename xlsx → 400 {"detail":"ParseError: ..."}. (b) upload >MAX_UPLOAD_MB → 413 Payload Too Large. Backend tidak crash (tidak ada 500). Evidence: curl response code + message, stderr server tidak ada traceback uncaught.

## Task 5: Halaman Admin UI (Upload + History List)
- **Status**: `pending`
- **Priority**: high
- **Depends On**: Task 4 (API admin siap)
- **Description**:
  - Template Jinja2 `app/templates/admin/upload.html` + `app/static/css/admin.css` + `app/static/js/admin.js`
  - Layout admin (satu halaman full):
    - Header: judul "Brand Mention Dashboard - Admin Panel", badge URL path aktif (contoh `/admin/<secret>`), link "Lihat Dashboard Publik →"
    - Section Upload:
      - Card dengan drag-drop area + tombol "Pilih File Excel" (input[type=file] accept=.xlsx,.xls)
      - Preview nama file terpilih, size
      - Progress bar upload (fake progress 10-90% sementara tunggu response)
      - Toast message box area: SUCCESS (hijau), ERROR (merah), INFO (biru) dengan close button
      - Catatan ukuran maksimal dan kolom yang dibutuhkan
    - Section Riwayat Upload:
      - Tombol "Refresh" untuk reload list
      - Tabel kolom: ID, Nama File Asli, Tanggal Upload, Jumlah Baris, Range Tanggal Data, Status (badge "AKTIF" hijau tebal / - abu), Tombol Aksi:
        - [Jadikan Aktif] (jika tidak aktif) → confirm dialog sederhana → POST set-active → refresh list + toast
        - [Reparse] (ikon loop) → POST reparse → toast
        - [Hapus] (ikon sampah merah) → confirm dialog "Yakin hapus?" → DELETE → hapus row dari tabel
      - Sortir default upload TERBARU di atas.
  - Design sistem: CSS variables untuk warna, card dengan border radius kecil, shadow lembut. Gunakan inline SVG Lucide icons (upload, trash-2, refresh-cw, check-circle, x-circle, alert-circle, external-link, file-spreadsheet).
  - JS: Fetch API, async/await, DOM manipulation vanilla, no framework. Validasi client-side extension & size sebelum upload (selain server-side double check).
- **Acceptance Criteria Addressed**: AC-1 (UI upload → aktif), AC-9 (list/set-active/delete UI), AC-3
- **Test Requirements**:
  - `rule` TR-5.1: Manual flow browser: Buka admin page, drag-drop file sample, tombol upload. (1) Progress bar muncul → (2) Upload selesai toast success HIJAU "Upload berhasil! Report menjadi aktif." → (3) Tabel riwayat langsung bertambah 1 row dengan badge "AKTIF" di row baru. (4) Klik "Lihat Dashboard Publik" → buka tab baru menampilkan dashboard dengan report itu. Evidence: screenshot langkah per langkah atau video pendek / recorded terminal logs browser.
  - `rule` TR-5.2: Halaman ada 10 riwayat. (1) Klik [Jadikan Aktif] row ke-5 → confirm Ya → row ke-5 berubah badge AKTIF, yang semula aktif jadi abu. Toast SUCCESS. (2) Klik [Hapus] row ke-7 → confirm → row hilang dari tabel, toast success. (3) Klik [Reparse] row ke-2 → loading spinner → toast "Reparse selesai". Evidence: Screenshot UI sebelum/sesudah + network tab request 200.
  - `rule` TR-5.3: Upload file invalid (mis. .txt rename .xlsx) via UI: toast ERROR MERAH muncul dengan pesan error detail dari response backend, file tidak masuk riwayat, TIDAK ada toast crash putih. Evidence: Screenshot toast error.
  - `rubric` TR-5.4: Kualitas UI admin. Scale 1-5 (1=teks doang, 3=form+s tabel dasar, 5=drag-drop area visual, progress bar, toast styled, badge aktif, icon SVG lucide di tiap tombol, kontras bagus). Threshold >=4. Evidence: Screenshot halaman admin penuh.

## Task 6: Halaman Dashboard Publik UI (Semua Visualisasi)
- **Status**: `pending`
- **Priority**: high
- **Depends On**: Task 4 (API /api/dashboard/active siap)
- **Description**:
  - Template `app/templates/public/dashboard.html` + `app/static/css/dashboard.css` + `app/static/js/dashboard.js`. Reuse base CSS variables dari admin.
  - Layout Dashboard (12-col CSS Grid, responsive):
    - **Header Bar**: (col span 12)
      - Judul: "Brand & Social Mention Analytics Dashboard"
      - Subtitle meta: Nama report, tanggal upload, range data (mis. "Data: 1 Okt 2026 (13 jam) · 2193 mentions")
      - Ikon kanan: [Refresh] (fetch ulang data tanpa reload page)
    - **KPI Row** (4 kolom desktop, 2 tablet, 1 mobile):
      1. Card Total Mentions: ikon message-square, angka besar (2193), sub "Total records"
      2. Card Est. Reach: ikon radio, angka Miliar/Juta format, sub "Total impressions potensial"
      3. Card Positif %: ikon thumbs-up, persentase + angka count, bar warna hijau tipis
      4. Card Sentimen Komposit: ikon activity bar, skor -1 s/d 1 (mis +0.40 label "Cenderung Positif") dengan indikator warna
    - **Charts Row 1**:
      - Kolom 6: Distribusi SOURCE (bar chart horizontal, warna per source, label count + %)
      - Kolom 6: Distribusi SENTIMEN (donut chart 3 bagian: netral abu, positif hijau, negatif merah. Center text jumlah total.)
    - **Charts Row 2**:
      - Kolom 8: Hourly Trend (bar chart vertikal per jam 00-23. Highlight jam puncak dengan warna beda + label "Puncak 10:00 · 717 mentions")
      - Kolom 4: EMOTION distribution (bar chart vertical 8 emosi)
    - **Charts Row 3**:
      - Kolom 6: Tracked Keyword Distribution (stacked bar 3 keyword, masing-masing pecah pos/neu/neg warna)
      - Kolom 6: Performance Score Distribution (bar chart 1-10 skala. Beri catatan skor 1 vs 10.)
    - **Charts Row 4**:
      - Kolom 12: Tabel TOP 20 HASHTAG (2 kolom: #hashtag, count, % dari total. Dengan scrollable 300px)
    - **Charts Row 5**:
      - Kolom 6: Engagement Metrics (tabel 8 metrik dengan kolom: Metrik, Total, Rata-rata, Tertinggi, N Valid)
      - Kolom 6: Top 10 Authors (list dengan nama, username, count post)
    - **Charts Row 6**:
      - Kolom 4: Bahasa (top 5 bar)
      - Kolom 4: Negara (top 5 bar, highlight Indonesia dengan flag via text IN)
      - Kolom 4: Demografi (Male/Female % gauge/double bar jika n_samples>0, jika 0 tampilkan placeholder "Tidak ada data demografi")
    - **Insight Box**: Summary auto-generate sederhana (kalimat string template berdasarkan data: "Puncak percakapan terjadi jam X dengan Y mentions. Sentimen didominasi ... dengan Z% positif. Platform terbesar ...")
  - **NO CHART LIBRARY EXTERNAL**: Semua chart render dengan DIV/CSS murni (bar width = percentage), SVG inline untuk donut (lingkaran stroke-dasharray), cukup. Tidak perlu Chart.js.
  - Lucide SVG inline untuk semua ikon card. TANPA SATU PUN EMOJI.
  - Jika /api/dashboard/active return ok=false → tampilkan full-page placeholder card: "Belum ada report aktif." dengan tombol ke admin path (jika user admin, link ke /admin/<secret>; tapi karena publik cukup informasikan hubungi admin).
  - Filter toggle sederhana: Dropdown "Filter Sumber" (All + list SOURCE unik yang ada). Jika dipilih, filter aggregasi per chart secara lokal (JavaScript) - TIDAK perlu hit server ulang.
- **Acceptance Criteria Addressed**: AC-2 (15+ elemen insight), AC-7 (responsive & design profesional), NFR-1 (vanilla), NFR-4
- **Test Requirements**:
  - `rule` TR-6.1: Data loaded dengan report aktif sample → hitung elemen visual yang ada: (KPI x4, Source bar, Sentiment donut, Hourly bar, Emotion bar, Keyword stacked, Performance bar, Hashtag table, Engagement table, Authors list, Language bar, Country bar, Demografi gauge, Insight box, Header meta) = >= 15 elemen ter-render dengan NON-ZERO / NON-EMPTY values. Evidence: Screenshot full dashboard scroll.
  - `rule` TR-6.2: Responsive test 3 ukuran: (1) 1920px (KPI 4 kolom rata, chart rows 2 kolom normal, tidak ada overflow X), (2) 768px (KPI 2 kolom, chart rows 1 kolom stacked, scroll vertikal lancar), (3) 375px iPhone SE (KPI 1 kolom, semua chart 1 kolom, teks tidak terpotong). Semua ukuran: tidak ada scroll HORIZONTAL di body. Evidence: 3 screenshot ukuran berbeda dari DevTools device mode.
  - `rubric` TR-6.3: Kualitas visualisasi chart CSS-only. Scale 1-5 (1=angka mentah tidak ada chart, 3=bar dasar polos, 5=warna gradasi konsisten, donut smooth dengan stroke, hourly peak di-highlight, hover tooltip tiap bar sederhana, label count dan % di setiap bar). Threshold >=4. Evidence: Zoomed screenshot 3 jenis chart.
  - `rule` TR-6.4: Fitur Filter Sumber: Pilih "instagram" dari dropdown → semua KPI dan chart menyesuaikan (Total Mentions berkurang sesuai jumlah instagram = 822, Source chart hanya instagram 100%, Sentimen disesuaikan). Kembali pilih "All" → data balik penuh. Evidence: Screenshot before/after filter.

## Task 7: Error Handling UI, Polish, Inline Lucide Icons SVG Konsolidasi
- **Status**: `pending`
- **Priority**: medium
- **Depends On**: Task 5, Task 6
- **Description**:
  - Buat shared `app/static/icons/lucide.svg` (sprite) atau inline langsung setiap icon via file per icon. Lebih baik inline di JS/CSS agar zero-request. Daftar minimal icon: upload, trash-2, refresh-cw, check-circle, x-circle, alert-circle, external-link, file-spreadsheet, message-square, radio, thumbs-up, activity, bar-chart-2, pie-chart, clock, hash, users, globe, languages, users-round, sparkles, filter.
  - Shared CSS: `app/static/css/shared.css` (import dari admin.css & dashboard.css) berisi reset, variable warna, toast styles, card styles, button styles, badge styles, typografi (system-ui sans-serif).
  - Tambah empty state component: jika data kosong (mis. demografi 0 sample, emotion 0 love), card tampilkan placeholder "Data tidak tersedia" dengan icon info, TIDAK tampilkan chart kosong hitam.
  - Loading state: Saat fetch `/api/dashboard/active` pertama kali → tampilkan skeleton loader untuk KPI cards dan charts (shine animation sederhana CSS).
  - Formatting helper JS: `formatNumber(num)` → 1.234, 1.2M, 1.5B sesuai magnitude. `formatPercent(num)` → 42.3%. `formatDate(dateStr)` → 1 Okt 2026 13:30 WIB.
  - Perbaiki accessibility minimal: semua tombol ada `aria-label`, warna contrast ratio minimal 4.5:1 untuk teks penting.
  - Tambah favicon simple SVG icon (dashboard chart mini inline <head>).
- **Acceptance Criteria Addressed**: AC-7 (polish design), NFR-7 (icons SVG lucide-style), NFR-5 (error UI jelas)
- **Test Requirements**:
  - `rule` TR-7.1: Cek konsistensi icon: (1) Semua tombol punya SVG icon lucide-style matching, (2) Tidak ada satupun karakter emoji di halaman dashboard maupun admin (grep source HTML dan rendered DOM). Evidence: `grep -r '[😀-🙏]' app/templates app/static || echo "NO EMOJI OK"` → output NO EMOJI OK. Screenshot halaman penuh inspeksi visual.
  - `rule` TR-7.2: Loading + empty state: (1) Disable network → buka dashboard → skeleton loader tampil bukan white screen. (2) Aktifkan report tanpa data demografi → card demografi tampil "Data tidak tersedia" bukan chart rusak. Evidence: Screenshot 2 state.
  - `rubric` TR-7.3: Konsistensi desain antar halaman admin & dashboard. Scale 1-5 (1=warna beda jauh, 3=mirip tapi beda spacing, 5=shared CSS variables, warna palette SAMA, font sama, card radius sama, shadow sama, padding konsisten 16/24px). Threshold >=4. Evidence: Side-by-side screenshot admin + dashboard.

## Task 8: End-to-End Smoke Test Full Application & Bug Fixes
- **Status**: `pending`
- **Priority**: medium
- **Depends On**: Task 7
- **Description**:
  - Jalankan server, lakukan skenario E2E penuh:
    S1. Upload file sample Excel dari admin → verifikasi report jadi aktif.
    S2. Buka dashboard publik → verifikasi semua KPI dan chart match dengan hasil analisis manual sebelumnya (total 2193, instagram 37.5%, jam 10 puncak 717).
    S3. Upload file lagi (sama) → verifikasi IDENTIK HASH tidak duplikat (history cuma bertambah jika beda konten).
    S4. Set report lama jadi aktif → dashboard berubah.
    S5. Hapus 1 report → file di storage benar-benar hilang.
    S6. Upload file txt yang di-rename xlsx → error toast di admin, tidak crash.
    S7. Cek responsivity di 3 ukuran.
    S8. Filter source di dashboard → KPI berubah benar.
  - Perbaiki semua bug yang ditemukan selama smoke test (task ini self-contained: fix bug langsung di sini).
  - Tulis `README.md` ringkas di root (bahasa Inggris sesuai user preference): cara `pip install -r requirements.txt`, `uvicorn main:app --reload`, ENV variables, penjelasan struktur.
- **Acceptance Criteria Addressed**: SEMUA AC (AC-1 s/d AC-9)
- **Test Requirements**:
  - `rule` TR-8.1: Skenario E2E S1-S8 di atas semua berjalan TANPA kegagalan. Setiap langkah S: (a) bukti visual screenshot, (b) tidak ada error 500 di log server, (c) output API match. Evidence: Checklist per S1-S8 dengan status PASS, lampirkan screenshot kunci atau command output.
  - `rule` TR-8.2: Performance NFR-2: Load dashboard dengan report 2193 baris → Network tab DevTools: request `/api/dashboard/active` selesai < 500ms (TTFB). Page load full (render semua chart) < 2 detik di laptop standar. Evidence: Network tab screenshot (Time column).
  - `rubric` TR-8.3: Developer experience (README + first-run). Scale 1-5 (1=butuh setup ribet, 3=run tapi perlu baca source, 5=README jelas step-by-step dengan command copy-paste, ENV ada template contoh, zero-config auto secret log). Threshold >=4. Evidence: Screenshot README dan log startup clean.
