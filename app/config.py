import os
import secrets
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

IS_VERCEL = bool(os.getenv("VERCEL")) or bool(os.getenv("VERCEL_ENV")) or bool(os.getenv("AWS_LAMBDA_FUNCTION_NAME"))

ADMIN_SECRET = os.getenv("ADMIN_SECRET", None)
GENERATED_SECRET_ON_STARTUP = False
if not ADMIN_SECRET:
    ADMIN_SECRET = secrets.token_urlsafe(24)
    GENERATED_SECRET_ON_STARTUP = True

if IS_VERCEL:
    _tmp_base = Path(os.getenv("VERCEL_TMPDIR", "/tmp")) / "vercel_data"
    UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", _tmp_base / "uploads"))
    PARSED_DIR = Path(os.getenv("PARSED_DIR", _tmp_base / "data_parsed"))
    DEFAULT_DB = Path(os.getenv("DB_PATH", BASE_DIR / "assets" / "dashboard.db"))
    DB_PATH = DEFAULT_DB
    ASSETS_DIR = BASE_DIR / "assets"
    try:
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        PARSED_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
else:
    UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", BASE_DIR / "uploads"))
    PARSED_DIR = Path(os.getenv("PARSED_DIR", BASE_DIR / "data_parsed"))
    DB_PATH = Path(os.getenv("DB_PATH", BASE_DIR / "dashboard.db"))
    ASSETS_DIR = BASE_DIR / "assets"

SAMPLE_BUNDLED_JSON = os.getenv("SAMPLE_BUNDLED_JSON", None)

MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "200"))

REQUIRED_COLUMNS = [
    "SOURCE",
    "DATE",
    "SENTIMENT",
    "TRACKED KEYWORD",
    "PERFORMANCE",
]

NUMERIC_COLUMNS = [
    "SOCIAL MEDIA INTERACTIONS",
    "REACH",
    "VISITS",
    "PERFORMANCE",
    "FOLLOWING",
    "LIKES",
    "SHARES",
    "COMMENTS",
    "VIEWS",
    "FAVOURITES",
]

STRING_CLEAN_COLUMNS = [
    "SOURCE",
    "TITLE",
    "TEXT",
    "TRACKED KEYWORD",
    "SENTIMENT",
    "EMOTION",
    "LANGUAGE",
    "COUNTRY",
    "AUTHOR NAME",
    "AUTHOR USERNAME",
]

for _p in (UPLOAD_DIR, PARSED_DIR):
    try:
        _p.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

try:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    pass
