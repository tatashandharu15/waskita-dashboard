# Brand Mention Analytics Dashboard

A full-stack web application for brand mention analytics with Excel upload,
admin-controlled reports, and a zero-build CSS-only visual dashboard.

## Key Features

### Admin Panel (protected by URL-secret)
- Drag-and-drop Excel upload (`.xlsx` / `.xls`) up to 200 MB
- Chunked streaming upload with size validation (413 when exceeds)
- Automatic report parsing into 16 analytics sections
- **Auto-active**: newest upload automatically becomes the active report
- Upload history table with:
  - Manual "Set Active" override
  - One-click "Reparse" to re-run the parser
  - "Delete" (removes row + `.xlsx` file + parsed JSON from disk)
- Idempotent uploads: identical file content (MD5 matched) is never duplicated

### Public Dashboard (no login, anyone can view)
Shows **only the currently active report** with 15+ visualisations and KPIs:

1. **4 KPI Cards**: Total Mentions, Total Reach (compact), Composite Sentiment, Peak Hour
2. **Horizontal Bar — Distribution by Source** (top 5 platforms, e.g. Instagram, Facebook, TikTok)
3. **Sentiment Donut** (Positive / Neutral / Negative) with composite score overlay
4. **Hourly Vertical Bar Chart** — 0–23h, peak hour highlighted in primary color
5. **Emotion Vertical Bar** — top 5 emotions
6. **Performance Histogram** — scores 1–10
7. **Keyword × Sentiment Stacked Bar** — top 3 keywords broken down by sentiment
8. **Top Hashtags Table** — rank, hashtag, count, share %
9. **Engagement 4-boxes** — Likes, Shares, Comments, Views
10. **Top Authors List** — avatar initials, username, mentions count
11. **Demographics Gauge** — Male / Female average percentages
12. **Languages (top 5)** horizontal bar
13. **Countries (top 5)** horizontal bar
14. **Insight Box** — dynamic natural-language summary of the period
15. **Negative Content Samples** — 5 highlighted negative mentions with title/author/snippet

Extra: local JS **Source filter** dropdown that recalculates KPIs on the fly
(no extra HTTP requests). Responsive at 3 breakpoints: 1920 → 768 → 375.

## Tech Stack

| Layer           | Choice                                                                |
| --------------- | --------------------------------------------------------------------- |
| Backend         | Python 3.10+, **FastAPI**, Uvicorn, Pandas, openpyxl, python-multipart |
| Templating      | HTML5 files + tiny `{{ VAR }}` string replacement (no Jinja2 rendering bugs) |
| Storage         | **SQLite** (upload history), **JSON files** (full parsed analytics), filesystem (.xlsx originals) |
| Auth (admin)    | **URL-secret steganography** — wrong secret returns HTTP 404; no login form |
| Frontend        | Vanilla HTML5, CSS3 Grid, vanilla JS ES2020 (`fetch`, `async/await`) |
| Build tooling   | **NONE** — no `package.json`, no bundler, no CDN deps                 |
| Icons           | Lucide-style inline SVG strings baked into the JS/CSS                 |
| Charts          | Pure CSS (flex widths) + SVG donuts & gauges                          |

## Requirements

- Python 3.10 or newer
- Pip
- 2 GB RAM comfortably handles 100k-row Excel files (Pandas in-memory)

## Installation

```bash
cd dashboard-analitic
python3 -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Run

### Quick start (auto-generated admin secret, printed on startup)
```bash
python3 -m uvicorn main:app --host 127.0.0.1 --port 8000
```

On startup the server prints a banner that includes your unique admin URL, e.g.:
```
======================================================================
  Admin URL     : http://localhost:8000/admin/ixnTsRe0HJw8iWTKfRMxjVp98Dn7i9V
  (auto-generated; set ENV ADMIN_SECRET to keep a fixed URL)
======================================================================
```

### Pin the admin URL (recommended for production)
```bash
export ADMIN_SECRET="your-very-long-hard-to-guess-string"
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### URLs

| Endpoint                    | Access | Purpose                                            |
| --------------------------- | ------ | -------------------------------------------------- |
| `/`                         | Public | Dashboard always showing the currently active report |
| `/api/dashboard/active`     | Public | JSON of the active report (used by dashboard JS)   |
| `/admin/<secret>`           | Admin  | Upload & history UI                                |
| `/admin/<secret>/api/upload` | Admin  | POST multipart `.xlsx`                             |
| `/admin/<secret>/api/uploads` | Admin | GET list history |
| `/admin/<secret>/api/uploads/{id}/set-active` | Admin | POST override active |
| `/admin/<secret>/api/uploads/{id}/reparse`    | Admin | POST rerun parser  |
| `/admin/<secret>/api/uploads/{id}`            | Admin | DELETE upload, xlsx, json |

## Expected Excel format

Excel files must include at least these 5 **required columns**:
`SOURCE`, `DATE`, `SENTIMENT`, `TRACKED KEYWORD`, `PERFORMANCE`.

Other supported optional columns (more columns → richer dashboard):
`TITLE`, `TEXT`, `SOCIAL MEDIA INTERACTIONS`, `REACH`, `VISITS`,
`EMOTION`, `LANGUAGE`, `COUNTRY`, `HAS AUTHOR`, `AUTHOR NAME`,
`AUTHOR USERNAME`, `FOLLOWING`,
`WEBSITE TRAFFIC DEMOGRAPHICS MALE` / `FEMALE`,
`LIKES`, `SHARES`, `COMMENTS`, `VIEWS`, `FAVOURITES`, `BOOKMARKED`, `TAGS`.

Cleaning rules built into the parser: blank strings → `Unknown`, numeric
columns strip `%` / `,` / spaces before conversion, dates are parsed with
Pandas fallback modes, hashtag extraction from `TEXT` / `TITLE`.

## Project Layout

```
dashboard-analitic/
├── main.py                    FastAPI entry, routes, analytics transform layer
├── requirements.txt
├── .gitignore
├── dashboard.db               Created at startup (SQLite)
├── app/
│   ├── config.py              ENV vars + directory setup
│   ├── db.py                  UploadRepository + SQLite CRUD
│   ├── parser.py              Pandas Excel parser (16 analytics sections)
│   ├── api_admin.py           Admin REST endpoints (upload, list, set-active, delete, reparse)
│   ├── templates/
│   │   ├── public/dashboard.html
│   │   └── admin/upload.html
│   └── static/
│       ├── css/{dashboard.css, admin.css}
│       └── js/{dashboard.js, admin.js}
├── uploads/                   Stored originals: {uuid}.xlsx
├── data_parsed/               Full JSON analytics: {uuid}.json
└── data/                      Sample Excel file (used for testing)
```

## Performance notes

- Parser and JSON load are both **lazy** (only run when needed)
- `/api/dashboard/active` for 2,193 rows → **< 1 ms TTFB warm** (cached JSON file)
- SQLite exclusive flag via single connection-per-request pattern
- Upload streaming chunk size = 64 KB; OOM-safe for the 200 MB cap
- Zero build step means instant deploys on any Python host

## Notes

- No cookies, no sessions, no CSRF tokens: admin security rests entirely on
  the URL-secret entropy. Use a ≥32-char random string from a CSPRNG in
  production, and always serve behind HTTPS.
- Dashboard is intentionally single-report; switching active reports is an
  admin action.
