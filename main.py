from pathlib import Path
from contextlib import asynccontextmanager
from typing import Dict, Any, List

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app import config
from app.db import UploadRepository, record_to_dict, get_upload_repository, PostgresUploadsRepository


BASE_DIR = Path(__file__).resolve().parent
if not (BASE_DIR / "app" / "static").is_dir() or not (BASE_DIR / "app" / "templates").is_dir():
    _cwd = Path.cwd()
    if (_cwd / "app" / "static").is_dir() and (_cwd / "app" / "templates").is_dir():
        BASE_DIR = _cwd
    elif (_cwd.parent / "app" / "static").is_dir() and (_cwd.parent / "app" / "templates").is_dir():
        BASE_DIR = _cwd.parent
STATIC_DIR = BASE_DIR / "app" / "static"
TEMPLATES_DIR = BASE_DIR / "app" / "templates"


def _render_template(template_rel: str, replacements: dict | None = None) -> str:
    path = TEMPLATES_DIR / template_rel
    raw = path.read_text(encoding="utf-8")
    if replacements:
        for k, v in replacements.items():
            raw = raw.replace("{{ " + k + " }}", str(v))
            raw = raw.replace("{{" + k + "}}", str(v))
    return raw


def transform_analytics_for_dashboard(a: Dict[str, Any]) -> Dict[str, Any]:
    if not a:
        return {}
    md = a.get("metadata") or {}
    ov_in = a.get("overview_kpi") or {}
    hourly = a.get("hourly_trend") or {}
    hourly_items = hourly.get("items") or []
    peak_hour = hourly.get("peak_hour")
    perf = a.get("performance_distribution") or {}
    engagement = a.get("engagement") or []

    eng_obj: Dict[str, int] = {}
    for e in engagement:
        key = (e.get("metric_key") or "").lower()
        total = int(e.get("total") or 0)
        if key == "likes": eng_obj["likes"] = total
        elif key == "shares": eng_obj["shares"] = total
        elif key == "comments": eng_obj["comments"] = total
        elif key == "views": eng_obj["views"] = total
        elif key == "reach": eng_obj["reach"] = total
        elif key == "social media interactions": eng_obj["interactions"] = total

    demo = a.get("demographics") or {}
    demo_out = {
        "male_pct": float(demo.get("male_avg_pct") or 0),
        "female_pct": float(demo.get("female_avg_pct") or 0),
        "n_samples": int(demo.get("n_samples") or 0),
    }

    kw_list = a.get("keyword_distribution") or []
    kw_array: List[Dict[str, Any]] = []
    crosstab_obj: Dict[str, Any] = {}
    for kw in kw_list:
        name = str(kw.get("name") or "")
        kw_array.append({
            "name": name,
            "count": int(kw.get("count") or 0),
            "percentage": float(kw.get("percentage") or 0),
        })
        cts = kw.get("sentiment_counts") or {}
        crosstab_obj[name] = {
            "positive": int(cts.get("positive") or 0),
            "neutral": int(cts.get("neutral") or 0),
            "negative": int(cts.get("negative") or 0),
        }

    ov_new = dict(ov_in)
    ov_new["peak_hour"] = peak_hour
    sc = float(ov_in.get("sentiment_composite") or ov_in.get("composite") or 0.0)
    ov_new["composite_sentiment"] = sc
    ov_new["composite"] = sc
    perf_mean_raw = float(perf.get("mean") or 0.0)
    ov_new["avg_performance"] = perf_mean_raw if perf_mean_raw else float(ov_in.get("mean_performance") or 0.0)
    reach_total = int(ov_in.get("total_reach_sum") or eng_obj.get("reach") or 0)
    ov_new["total_reach"] = reach_total
    ov_new["total_mentions"] = int(md.get("rows_count") or ov_in.get("total_mentions") or 0)
    ov_new["total_interactions"] = int(eng_obj.get("interactions") or 0)

    perf_scores = perf.get("scores") or []
    perf_hist = [{"score": s.get("score"), "count": int(s.get("count") or 0)} for s in perf_scores]

    sent_raw = a.get("sentiment_distribution") or {}
    sent_list = []
    total_rows = int(md.get("rows_count") or 1)
    if isinstance(sent_raw, dict):
        for sname in ("positive", "neutral", "negative"):
            sdata = sent_raw.get(sname) or {}
            if isinstance(sdata, dict):
                cnt = int(sdata.get("count") or 0)
                pct = sdata.get("percentage")
                if pct is None:
                    pct = round(cnt * 100.0 / total_rows, 2) if total_rows else 0
                sent_list.append({"name": sname, "count": cnt, "percentage": pct})
            else:
                cnt = int(sdata or 0)
                pct = round(cnt * 100.0 / total_rows, 2) if total_rows else 0
                sent_list.append({"name": sname, "count": cnt, "percentage": pct})
    elif isinstance(sent_raw, list):
        for s in sent_raw:
            sn = s.get("name") or s.get("sentiment") or s.get("label") or ""
            cnt = int(s.get("count") or 0)
            pct = s.get("percentage")
            if pct is None:
                pct = round(cnt * 100.0 / total_rows, 2) if total_rows else 0
            sent_list.append({"name": str(sn), "count": cnt, "percentage": pct})

    lang_in = a.get("language_distribution") or []
    lang_out = []
    for l in lang_in:
        nm = l.get("name") or l.get("lang") or l.get("language") or "Unknown"
        lang_out.append({"name": str(nm), "count": int(l.get("count") or 0), "percentage": l.get("percentage", 0)})

    cntry_in = a.get("country_distribution") or []
    cntry_out = []
    for c in cntry_in:
        nm = c.get("name") or c.get("country") or c.get("nation") or "Unknown"
        cntry_out.append({"name": str(nm), "count": int(c.get("count") or 0), "percentage": c.get("percentage", 0)})

    authors_in = a.get("top_authors") or []
    authors_out = []
    for au in authors_in:
        authors_out.append({
            "name": au.get("name") or au.get("author_name") or "",
            "username": au.get("username") or au.get("author_username") or "",
            "count": int(au.get("count") or 0),
            "reach": int(au.get("reach") or au.get("total_reach") or 0),
        })

    neg_in = a.get("negative_sample") or []
    neg_out = []
    for n in neg_in:
        txt = n.get("text_preview") or n.get("text") or n.get("content") or ""
        src = n.get("source") or n.get("SOURCE") or "Unknown"
        title_guess = str(txt).strip().split("\n")[0][:120] if txt else "Sample negatif"
        author_val = n.get("author_name") or n.get("author") or n.get("AUTHOR NAME") or ""
        neg_out.append({
            "title": title_guess,
            "author": author_val or "Unknown Author",
            "text": str(txt),
            "sentiment": "negative",
            "source": str(src),
        })

    return {
        "metadata": md,
        "overview": ov_new,
        "source": a.get("source_distribution") or [],
        "keyword": kw_array,
        "sentiment_crosstab_by_keyword": crosstab_obj,
        "sentiment": sent_list,
        "emotion": a.get("emotion_distribution") or [],
        "hourly": hourly_items,
        "top_hashtags": a.get("top_hashtags") or [],
        "performance_histogram": perf_hist,
        "engagement_summary": eng_obj if eng_obj else {"likes": 0, "shares": 0, "comments": 0, "views": 0, "reach": 0, "interactions": 0},
        "language": lang_out,
        "country": cntry_out,
        "top_authors": authors_out,
        "demographics": demo_out,
        "negative_sample": neg_out,
        "sentiment_per_source": a.get("sentiment_per_source") or [],
        "top_words": a.get("top_words") or [],
        "emoji_frequency": a.get("emoji_frequency") or [],
        "all_mentions": a.get("all_mentions") or [],
    }


IS_VERCEL_RUNTIME = config.IS_VERCEL


if not IS_VERCEL_RUNTIME:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        repo = get_upload_repository()
        if hasattr(repo, "init_db"):
            try:
                repo.init_db()
            except Exception:
                pass
        app.state.repo = repo
        banner_lines = []
        banner_lines.append("")
        banner_lines.append("=" * 70)
        banner_lines.append("Waskita Analytics Dashboard")
        banner_lines.append("=" * 70)
        if isinstance(repo, PostgresUploadsRepository):
            banner_lines.append(f"  Storage Mode  : PERMANENT (Vercel Postgres + Blob)")
        else:
            banner_lines.append(f"  Storage Mode  : SQLite (Local/Fallback)")
            banner_lines.append(f"  SQLite DB     : {config.DB_PATH}")
            banner_lines.append(f"  Uploads dir   : {config.UPLOAD_DIR}")
            banner_lines.append(f"  Parsed JSON   : {config.PARSED_DIR}")
        banner_lines.append(f"  Max upload    : {config.MAX_UPLOAD_MB} MB")
        if config.GENERATED_SECRET_ON_STARTUP:
            banner_lines.append(f"  Admin URL     : http://localhost:8000/admin/{config.ADMIN_SECRET}")
            banner_lines.append("  (auto-generated; set ENV ADMIN_SECRET to keep a fixed URL)")
        else:
            banner_lines.append(f"  Admin URL     : http://localhost:8000/admin/{config.ADMIN_SECRET}")
        banner_lines.append("=" * 70)
        banner_lines.append("")
        print("\n".join(banner_lines), flush=True)
        yield

    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None)
else:
    app = FastAPI(docs_url=None, redoc_url=None)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def get_repo(request: Request):
    if not hasattr(request.app.state, "repo") or request.app.state.repo is None:
        try:
            request.app.state.repo = get_upload_repository()
        except Exception:
            request.app.state.repo = UploadRepository.__new__(UploadRepository)
            request.app.state.repo.db_path = config.DB_PATH
            request.app.state.repo._db_init_ok = False
            request.app.state.repo._bundled_record_cache = None
    return request.app.state.repo


def validate_secret(secret: str) -> None:
    if secret != config.ADMIN_SECRET:
        raise HTTPException(status_code=404, detail="Not Found")


@app.get("/api/dashboard/active")
async def api_dashboard_active(request: Request):
    repo = get_repo(request)
    rec = repo.get_active()
    if not rec:
        return JSONResponse(
            {
                "ok": False,
                "message": "No active report yet. Please upload a report from the admin page.",
                "admin_path": f"/admin/{config.ADMIN_SECRET}",
            }
        )
    analytics_raw = repo.load_parsed_json(rec.id) or {}
    analytics = transform_analytics_for_dashboard(analytics_raw)
    return JSONResponse(
        {
            "ok": True,
            "upload_id": rec.id,
            "upload_meta": record_to_dict(rec),
            "analytics": analytics,
        }
    )


@app.get("/", response_class=HTMLResponse)
async def public_dashboard(request: Request):
    try:
        html = _render_template("public/dashboard.html")
        return HTMLResponse(html)
    except Exception as exc:
        import traceback as _tb, json as _json
        err = {
            "error": "TEMPLATE_RENDER_FAILED",
            "message": str(exc),
            "type": exc.__class__.__name__,
            "traceback": _tb.format_exc(limit=8),
            "paths_debug": {
                "BASE_DIR_main": str(BASE_DIR),
                "STATIC_DIR_exists": STATIC_DIR.exists(),
                "TEMPLATES_DIR_exists": TEMPLATES_DIR.exists(),
                "TEMPLATES_DIR": str(TEMPLATES_DIR),
                "dashboard_html_path": str(TEMPLATES_DIR / "public/dashboard.html"),
                "dashboard_html_exists": (TEMPLATES_DIR / "public/dashboard.html").exists(),
                "list_templates_dir": list(sorted(p.name for p in TEMPLATES_DIR.rglob("*"))) if TEMPLATES_DIR.exists() else [],
                "BASE_DIR_main_exists_mainpy": (BASE_DIR / "main.py").exists(),
                "BASE_DIR_main_exists_appdir": (BASE_DIR / "app").is_dir(),
                "cwd": str(Path.cwd()),
            },
        }
        if STATIC_DIR.exists():
            err["paths_debug"]["list_static_top10"] = list(sorted(p.relative_to(BASE_DIR).as_posix() for p in STATIC_DIR.rglob("*")))[:10]
        if config.IS_VERCEL:
            err["paths_debug"]["Vercel_env"] = {
                "VERCEL": bool(__import__("os").getenv("VERCEL")),
                "VERCEL_ENV": __import__("os").getenv("VERCEL_ENV"),
                "AWS_LAMBDA_FUNCTION_NAME": __import__("os").getenv("AWS_LAMBDA_FUNCTION_NAME"),
                "LAMBDA_TASK_ROOT": __import__("os").getenv("LAMBDA_TASK_ROOT"),
            }
        import sys as _sys
        _sys.stderr.write("ROUTE / RENDER ERROR " + _json.dumps(err, ensure_ascii=False, default=str)[:5000] + "\n")
        _sys.stderr.flush()
        plain = _json.dumps(err, ensure_ascii=False, indent=2, default=str)
        return HTMLResponse(
            content="<html><head><meta charset='utf-8'><title>500 Render Error</title></head><body><h1>500 Internal Server Error (route /)</h1><pre style='white-space:pre-wrap;background:#fee;padding:16px;'>" + plain.replace("<", "&lt;") + "</pre></body></html>",
            status_code=500,
        )


@app.get("/admin", response_class=HTMLResponse)
@app.get("/admin/", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    is_vc = bool(config.IS_VERCEL)
    html = _render_template(
        "admin/login.html",
        {
            "IS_VERCEL": config.IS_VERCEL,
            "IS_VERCEL_BOOL": "true" if is_vc else "false",
            "IS_VERCEL_TAG": "Production Vercel" if is_vc else "Local",
        },
    )
    return HTMLResponse(html)


@app.get("/admin/{secret}", response_class=HTMLResponse)
async def admin_home(request: Request, secret: str):
    validate_secret(secret)
    is_vc = bool(config.IS_VERCEL)
    is_perm = bool(config.IS_PERMANENT_MODE)
    html = _render_template(
        "admin/upload.html",
        {
            "ADMIN_SECRET": secret,
            "ADMIN_PATH": f"/admin/{secret}",
            "DASHBOARD_PATH": "/",
            "IS_VERCEL": config.IS_VERCEL,
            "IS_VERCEL_BOOL": "true" if is_vc else "false",
            "IS_PERMANENT_BOOL": "true" if is_perm else "false",
        },
    )
    return HTMLResponse(html)


from app.api_admin import router as admin_router

app.include_router(admin_router)
