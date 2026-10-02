# Brand Mention Analytics Dashboard - Product Requirements Document

## Overview
- **Summary**: Aplikasi web dashboard analytics untuk brand/social mention dengan dua area utama: (1) Admin page dengan proteksi URL secret untuk meng-upload file Excel Mentions Report, (2) Dashboard publik yang selalu menampilkan report TERBARU dalam bentuk visualisasi interaktif (sentimen, sumber, keyword, tren per jam, engagement, dll).
- **Purpose**: Mempermudah administrator untuk upload data mention mentah dan menyajikan insight analytics secara realtime kepada stakeholder tanpa login.
- **Target Users**:
  - Admin: tim media monitoring / PR yang upload file Excel
  - Public Viewer: stakeholder (manajemen, tim komunikasi, klien) yang hanya melihat dashboard

## Goals
- Admin bisa upload file Excel Mentions Report melalui URL secret tanpa login form
- Sistem otomatis mem-parsing Excel, menghitung statistik, dan menyimpan hasilnya
- Dashboard publik menampilkan report upload TERBARU dengan visualisasi lengkap (mirip hasil analisis sebelumnya: overview, sentimen, source, keyword, hourly trend, engagement, top hashtags, performance, emosi)
- Semua visualisasi interaktif (hover info, filter sederhana) dan responsive
- Zero-build frontend: vanilla JS + HTML + CSS tanpa bundler
- Ringan, bisa dijalankan tanpa dependency eksternal berat

## Non-Goals
- Tidak ada user management / multi-user role system
- Tidak ada kolaborasi realtime antar user
- Tidak ada edit data manual (hanya upload → parse → display)
- Tidak ada export PDF/CSV report dari UI (bisa ditambahkan nanti)
- Tidak ada multi-report selector di landing page publik (hanya single report aktif terbaru)
- Bukan untuk data realtime streaming (hanya batch upload)

## Background & Context
- Proyek ini berisi 1 file Excel sample: `data/kapolri - Mentions_Report - 2026-10-01.xlsx` (2193 rows, 27 columns) yang menjadi acuan struktur data
- Analisis manual sebelumnya menunjukkan 18 area insight yang harus disajikan dashboard (overview, source, keyword, sentiment, emotion, hourly, hashtags, performance, engagement, authors, demographics, bahasa, negara, dst)
- Preferensi teknis pemilik proyek: FastAPI backend, vanilla JS HTML/CSS frontend (zero-build), SQLite + File JSON storage, Lucide-style SVG icons, tanpa emoji di dashboard profesional

## Functional Requirements
### Admin Area
- **FR-1**: URL secret admin (config via env var) yang ketika diakses menampilkan upload page
- **FR-2**: Form upload file Excel (.xlsx / .xls) dengan validasi MIME type dan ekstensi
- **FR-3**: Setelah upload → sistem parse Excel secara otomatis dan hitung semua metrik analytics
- **FR-4**: Menampilkan list history uploads (10 terakhir) dengan metadata (tanggal upload, nama file, jumlah baris, range tanggal data, summary sentimen, tombol "Jadikan Aktif" dan "Hapus")
- **FR-5**: Admin bisa menghapus upload lama dari history
- **FR-6**: Tombol refresh / re-parse untuk upload tertentu jika schema parser berubah
- **FR-7**: Setiap upload otomatis langsung menjadi "Report Aktif" yang ditampilkan di dashboard publik (namun admin bisa override dan memilih report lama untuk dijadikan aktif)

### Public Dashboard Area
- **FR-8**: Halaman root `/` selalu menampilkan report yang saat ini ditandai "aktif"
- **FR-9**: Menampilkan Header dengan: nama report aktif, tanggal upload, range tanggal data, jumlah total mentions, dan tombol refresh (reload data tanpa reload page)
- **FR-10**: Card Summary (KPIs): Total Mentions, Total Reach (est), % Positif, % Negatif, Sentimen Score (skor komposit)
- **FR-11**: Chart donat/bar: Distribusi SOURCE (platform)
- **FR-12**: Chart bar: Distribusi TRACKED KEYWORD + komposisi sentimennya
- **FR-13**: Chart donat/bar: Distribusi SENTIMEN (Neutral/Positive/Negative)
- **FR-14**: Chart donat/bar: Distribusi EMOSI (Love/Joy/Anger/...)
- **FR-15**: Chart line/bar hourly: MENTIONS PER JAM (active date) dengan indikator waktu puncak
- **FR-16**: Tabel / bar: TOP 20 HASHTAG dengan count + persentase
- **FR-17**: Score performance distribution: distribusi skor Performance 1-10 + % top performers
- **FR-18**: Tabel / bar: TOP AUTHORS (jumlah post terbanyak, 10 besar)
- **FR-19**: Tabel / ringkasan: ENGAGEMENT METRICS (total & avg reach, likes, shares, comments, views)
- **FR-20**: Demografi website (male/female %) untuk source site/news jika data tersedia
- **FR-21**: Bahasa + Negara distribusi
- **FR-22**: Filter toggle sederhana: filter by SOURCE untuk menyesuaikan semua chart (opsional tapi sangat diinginkan)
- **FR-23**: Jika belum ada report aktif → tampilkan landing placeholder "Belum ada report. Silakan upload dari halaman admin."

### Parser / Data Layer
- **FR-24**: Mendukung struktur Excel dengan kolom: SOURCE, TITLE, URL, TEXT, DATE, TRACKED KEYWORD, SOCIAL MEDIA INTERACTIONS, REACH, VISITS, PERFORMANCE, SENTIMENT, EMOTION, LANGUAGE, COUNTRY, HAS AUTHOR, AUTHOR NAME, AUTHOR USERNAME, FOLLOWING, WEBSITE TRAFFIC DEMOGRAPHICS MALE/FEMALE, LIKES, SHARES, COMMENTS, VIEWS, FAVOURITES, BOOKMARKED, TAGS
- **FR-25**: Robust parsing: kolom kosong di-handle (konversi ke NaN / 0 / unknown sesuai konteks)
- **FR-26**: Parsing DATE otomatis (mendukung berbagai format datetime string)
- **FR-27**: Numeric cleaning: konversi string dengan spasi / percent sign ke angka

### API
- **FR-28**: `GET /api/dashboard/active` → return JSON data report aktif lengkap (semua aggregasi siap pakai frontend)
- **FR-29**: `POST /api/admin/<secret>/upload` → multipart upload file, return upload metadata
- **FR-30**: `GET /api/admin/<secret>/uploads` → list semua upload
- **FR-31**: `POST /api/admin/<secret>/uploads/<id>/set-active` → jadikan report aktif
- **FR-32**: `DELETE /api/admin/<secret>/uploads/<id>` → hapus upload beserta file data
- **FR-33**: `POST /api/admin/<secret>/uploads/<id>/reparse` → re-parse file asli dan update agregasi

## Non-Functional Requirements
- **NFR-1 (Zero-build Frontend)**: HTML/CSS/JS vanilla tanpa bundler/transpiler. Buka file HTML via FastAPI static files langsung jalan.
- **NFR-2 (Performance Dashboard)**: Load report aktif < 2 detik untuk data 5000 baris (report 2193 baris sample harus < 500ms)
- **NFR-3 (Zero-config startup)**: Clone repo + install requirements + `uvicorn main:app` langsung jalan tanpa setup tambahan. SQLite DB dibuat otomatis, folder uploads otomatis, default admin secret di-generate random jika tidak diset ENV (ditampilkan di log startup).
- **NFR-4 (Responsive)**: Dashboard tampil baik di desktop 1920px, laptop 1366px, dan tablet 768px. Mobile 375px tidak pecah (tampilan kolom vertikal).
- **NFR-5 (Error handling)**: Upload Excel gagal (format salah, kolom kurang) → pesan error jelas di UI, tidak crash backend.
- **NFR-6 (Idempotent)**: Upload file yang sama persis (hash identik) tidak membuat duplikat upload baru, tapi bisa gunakan yang sudah ada.
- **NFR-7 (Iconography)**: Semua icon menggunakan SVG Lucide-style inline atau sprite, tidak ada emoji, tidak ada icon font (CDN).
- **NFR-8 (Visual Design)**: Color palette profesional (monokrom + 2 aksen warna), tipografi sans-serif system, spacing konsisten, card-based layout, grid rapi.

## Constraints
- **Technical**:
  - Backend: Python 3.10+ dengan FastAPI, Uvicorn, Pandas, openpyxl
  - Frontend: HTML5 + CSS3 (CSS Grid + Flexbox) + Vanilla JS ES2020 (fetch, async/await)
  - Storage: SQLite (via SQLAlchemy atau stdlib sqlite3) + folder `uploads/` untuk file asli + folder `data_parsed/` untuk JSON aggregasi
  - Tanpa npm / node / bundler sama sekali di frontend
  - Tanpa CDN dependency (semua asset self-hosted)
- **Business**:
  - Admin secret URL tidak boleh mudah ditebak (min 32 chars random jika auto-generate)
  - Tidak boleh ada UI "login admin" (sesuai user choice: URL secret only)
  - Hanya satu report aktif yang ditampilkan publik
- **Dependencies**:
  - pypi: `fastapi`, `uvicorn[standard]`, `pandas`, `openpyxl`, `python-multipart` (untuk upload)
  - stdlib: `sqlite3`, `hashlib`, `json`, `datetime`, `pathlib`, `os`, `re`

## Assumptions
- File Excel upload selalu mengikuti kolom Mentions Report yang sama dengan file sample (atau minimal kolom kunci ada: SOURCE, TEXT, DATE, TRACKED KEYWORD, SENTIMENT, PERFORMANCE)
- Pengguna admin akan menyimpan URL secret dengan aman (tidak ada mekanisme reset password/lupa URL)
- Traffic dashboard tidak melebihi ribuan request per hari (cocok untuk penggunaan internal/klien terbatas)
- Server memiliki memori cukup untuk Pandas memproses Excel sampai ~50.000 baris
- Jika file terlalu besar (>100MB), admin akan memotong / sampling terlebih dahulu

## Acceptance Criteria

### AC-1: Admin dapat upload file Excel dan menjadi report aktif otomatis
- **Type**: `rule`
- **Given**: Server berjalan, admin mengakses URL secret admin
- **When**: Admin memilih file Excel Mentions Report yang valid dan klik Upload
- **Then**: (1) File tersimpan di folder uploads, (2) SQLite mencatat record upload baru, (3) JSON aggregasi terbentuk di data_parsed/, (4) Upload baru otomatis menjadi report aktif, (5) Halaman admin menampilkan upload baru di list dengan status "Aktif"
- **Pass Condition**: Semua 5 kondisi terpenuhi; verifikasi via upload file sample dan cek list history + cek API `/api/dashboard/active` return data sesuai
- **Evidence**: Screenshot / curl response + DB query + file listing

### AC-2: Dashboard publik menampilkan semua 15+ elemen insight dari hasil analisis
- **Type**: `rubric`
- **Dimension**: Kelengkapan visualisasi dashboard terhadap 18 area insight dari analisis manual
- **Scale**: 1-5
  - 1 = < 5 elemen ditampilkan
  - 3 = 8-12 elemen ditampilkan dengan chart sederhana (bar text)
  - 5 = >= 15 elemen ditampilkan dengan visualisasi tepat (chart, tabel, card KPI, hourly line/bar, donut/bar sentiment)
- **Pass Threshold**: >= 4
- **Evidence**: Screenshot halaman dashboard penuh + inspeksi DOM / JS console bahwa semua elemen ter-render dengan benar sesuai data aktif

### AC-3: Proteksi admin URL secret berjalan (tidak ada login form)
- **Type**: `rule`
- **Given**: Server berjalan, `ADMIN_SECRET=rahasia123`
- **When**: (a) Mengakses `/admin/rahasia123` → (b) Mengakses `/admin/salah-url`
- **Then**: Skenario (a) menampilkan upload form (status 200). Skenario (b) return 404 atau redirect ke `/` tanpa menampilkan apapun. TIDAK ADA halaman login form di manapun.
- **Pass Condition**: Kedua skenario sesuai; tidak ada /login /admin tanpa secret tidak menampilkan form upload
- **Evidence**: curl request untuk kedua URL + status code + content snippet

### AC-4: Zero-build frontend berjalan tanpa npm/bundler
- **Type**: `rule`
- **Given**: Repo di-clone, `pip install -r requirements.txt` dijalankan, `uvicorn main:app --reload`
- **When**: Browser membuka `http://localhost:8000/` dan halaman admin secret
- **Then**: (1) Tidak ada file `package.json` / `node_modules` di repo, (2) Dashboard aktif ter-render lengkap dengan chart, (3) Tidak ada error 404 di Network tab DevTools, (4) Tidak ada error JS di Console
- **Pass Condition**: Keempat kondisi. Verifikasi: `ls package.json 2>/dev/null` gagal, Network tab semua asset 200 OK, Console kosong error
- **Evidence**: Bukti file listing + browser DevTools screenshot/curl

### AC-5: Report aktif selalu menampilkan upload TERBARU (atau yang dijadikan aktif manual)
- **Type**: `rule`
- **Given**: Ada 3 upload history (A, B, C dengan C terbaru = aktif)
- **When**: (1) Upload file baru D → (2) Buka `/` → (3) Kembali ke admin, klik "Jadikan Aktif" pada upload A → (4) Buka `/` lagi
- **Then**: Setelah (1)(2): `/` menampilkan report D. Setelah (3)(4): `/` menampilkan report A sesuai pilihan manual
- **Pass Condition**: Pergantian report aktif berjalan otomatis saat upload baru, dan bisa override manual. Cek via API `/api/dashboard/active` upload_id sesuai
- **Evidence**: Log upload + API response before/after set-active

### AC-6: Parser robust menangani edge case data
- **Type**: `rule`
- **Given**: File Excel sample 2193 baris (dengan banyak cell kosong ' ', date string, numeric dengan spasi, percent string)
- **When**: File sample di-upload dan di-parse
- **Then**: (1) DATE berhasil di-parse menjadi datetime untuk >= 95% baris, (2) Numeric kolom (PERFORMANCE, LIKES, REACH, dll) dikonversi ke angka tanpa NaN bocor ke aggregasi, (3) String kosong ' ' di EMOTION/COUNTRY/LANGUAGE dikonversi ke 'Unknown', (4) Hourly chart aggregasi benar (0-23 jam) untuk tanggal aktif, (5) Total hitung mention = 2193 sesuai
- **Pass Condition**: Kelima poin. Verifikasi JSON output `/api/dashboard/active` : total = 2193, hourly ada, numeric stats masuk akal
- **Evidence**: Print output aggregasi JSON (fields kunci)

### AC-7: Desain dashboard profesional & responsive
- **Type**: `rubric`
- **Dimension**: Kualitas visual UI dashboard (kebersihan layout, spacing, konsistensi, responsive, non-emoji)
- **Scale**: 1-5
  - 1 = Berantakan, tabrakan layout, emoji ada di mana-mana
  - 3 = Layout rapi, grid dasar, spacing lumayan, emoji sudah dihilangkan namun icon masih kurang
  - 5 = Grid rapi 12-col, card dengan shadow/border elegan, spacing konsisten 8px base, icon Lucide SVG proporsional di tiap section header, tidak ada satupun emoji, responsive: desktop (3 col card row) → tablet (2 col) → mobile (1 col) tanpa overflow horizontal
- **Pass Threshold**: >= 4
- **Evidence**: Screenshot 3 ukuran viewport (1920, 768, 375px) + inspeksi CSS untuk responsive breakpoints

### AC-8: Error handling upload file invalid
- **Type**: `rule`
- **Given**: Admin upload (a) file .txt rename jadi .xlsx, (b) file xlsx tapi tidak ada kolom SOURCE/DATE/SENTIMEN, (c) file > 200MB
- **When**: Ketiga file di-upload via form
- **Then**: (a)(b)(c) return pesan error YANG JELAS di UI (toast / alert box di atas form), tidak ada 500 crash. File invalid tidak tersimpan di DB dan folder uploads.
- **Pass Condition**: Ketiga skenario tidak menyebabkan backend crash, user tahu apa yang salah
- **Evidence**: Screenshot pesan error + log server tidak ada traceback

### AC-9: History upload admin (list, set-active, delete)
- **Type**: `rule`
- **Given**: Ada 5 upload history di DB
- **When**: Admin (1) Klik "Jadikan Aktif" pada upload ke-3 → (2) Klik "Hapus" pada upload ke-4 → (3) Refresh halaman list
- **Then**: (1) Upload ke-3 punya label "Aktif", status aktif di DB berubah, (2) Upload ke-4 hilang dari list, file asli di uploads/ dan JSON di data_parsed/ ikut terhapus, (3) List sekarang berisi 4 upload dengan upload-3 aktif
- **Pass Condition**: Operasi list/set-active/delete berjalan sesuai
- **Evidence**: DB dump sebelum/sesudah + file listing uploads/data_parsed sebelum/sesudah delete

## Open Questions
- [x] Jenis auth admin: URL Secret (confirmed user)
- [x] Storage: SQLite + File JSON (confirmed)
- [x] Akses dashboard: Publik tanpa login (confirmed)
- [x] Mode dashboard: Single report aktif terbaru + override manual (confirmed)
- [ ] Port default production? (asumsi 8000, setup via env)
- [ ] Maksimum file size upload? (asumsi 200MB, bisa dikonfigurasi)
