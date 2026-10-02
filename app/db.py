import sqlite3
import json
import uuid
import hashlib
import shutil
import os
from pathlib import Path
from typing import Optional, List, Any, Dict, Callable
from dataclasses import dataclass, asdict, field
from datetime import datetime

from . import config


ASSETS_DIR = config.ASSETS_DIR
BASE_DIR = config.BASE_DIR
VIRTUAL_BUNDLED_RECORD_ID = 9999


@dataclass
class UploadRecord:
    id: int
    filename_original: str
    filename_stored: str
    file_hash: str
    rows_count: int
    min_date: Optional[str]
    max_date: Optional[str]
    uploaded_at: str
    is_active: int
    parsed_json_path: str
    summary_json: str = "{}"
    _summary_cache: Optional[Dict[str, Any]] = field(default=None, repr=False)
    bundled_virtual: bool = False

    @property
    def summary(self) -> Dict[str, Any]:
        if self._summary_cache is None:
            try:
                self._summary_cache = json.loads(self.summary_json)
            except Exception:
                self._summary_cache = {}
        return self._summary_cache


class UploadRepository:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or config.DB_PATH
        try:
            self.init_db()
            self._db_init_ok = True
        except Exception:
            self._db_init_ok = False
        self._bundled_record_cache: Optional[UploadRecord] = None

    def _conn(self) -> sqlite3.Connection:
        db_str = str(self.db_path)
        try_mode_ro_first = config.IS_VERCEL or (not os.access(str(self.db_path.parent if self.db_path.parent.exists() else Path('.')), os.W_OK))
        if try_mode_ro_first:
            try:
                uri = "file:" + db_str + "?mode=ro"
                conn = sqlite3.connect(uri, uri=True)
                conn.row_factory = sqlite3.Row
                return conn
            except Exception:
                pass
        try:
            conn = sqlite3.connect(db_str)
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.OperationalError:
            try:
                uri = "file:" + db_str + "?mode=ro"
                conn = sqlite3.connect(uri, uri=True)
                conn.row_factory = sqlite3.Row
                return conn
            except Exception:
                raise

    def init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with self._conn() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS uploads (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        filename_original TEXT NOT NULL,
                        filename_stored TEXT NOT NULL,
                        file_hash TEXT NOT NULL UNIQUE,
                        rows_count INTEGER NOT NULL DEFAULT 0,
                        min_date TEXT,
                        max_date TEXT,
                        uploaded_at TEXT NOT NULL,
                        is_active INTEGER NOT NULL DEFAULT 0,
                        summary_json TEXT NOT NULL DEFAULT '{}',
                        parsed_json_path TEXT NOT NULL
                    )
                    """
                )
                conn.commit()
        except sqlite3.OperationalError:
            return

    def _row_to_record(self, row: sqlite3.Row) -> UploadRecord:
        return UploadRecord(
            id=row["id"],
            filename_original=row["filename_original"],
            filename_stored=row["filename_stored"],
            file_hash=row["file_hash"],
            rows_count=row["rows_count"],
            min_date=row["min_date"],
            max_date=row["max_date"],
            uploaded_at=row["uploaded_at"],
            is_active=row["is_active"],
            summary_json=row["summary_json"] or "{}",
            parsed_json_path=row["parsed_json_path"],
        )

    def _clear_all_active(self, conn: sqlite3.Connection) -> None:
        conn.execute("UPDATE uploads SET is_active = 0 WHERE is_active = 1")

    def create_upload(
        self,
        filename_original: str,
        temp_file_path: Path,
        parsed_dict: Dict[str, Any],
        rows_count: int,
        min_date: Optional[str],
        max_date: Optional[str],
    ) -> UploadRecord:
        file_hash = self._hash_file(temp_file_path)

        with self._conn() as conn:
            existing = conn.execute(
                "SELECT * FROM uploads WHERE file_hash = ?", (file_hash,)
            ).fetchone()
            if existing:
                rec = self._row_to_record(existing)
                self._clear_all_active(conn)
                conn.execute(
                    "UPDATE uploads SET is_active = 1 WHERE id = ?", (rec.id,)
                )
                conn.commit()
                return rec

        stored_uuid = str(uuid.uuid4())
        stored_xlsx = f"{stored_uuid}.xlsx"
        stored_json = f"{stored_uuid}.json"
        stored_path = config.UPLOAD_DIR / stored_xlsx
        json_path = config.PARSED_DIR / stored_json

        shutil.copyfile(str(temp_file_path), str(stored_path))
        json_path.write_text(
            json.dumps(parsed_dict, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

        meta = parsed_dict.get("overview_kpi", {})
        summary = {
            "total_mentions": rows_count,
            "pct_positive": meta.get("pct_positive", 0),
            "pct_negative": meta.get("pct_negative", 0),
            "pct_neutral": meta.get("pct_neutral", 0),
            "sentiment_composite": meta.get("sentiment_composite", 0),
            "total_reach": meta.get("total_reach_sum", 0),
            "top_source": (
                parsed_dict.get("source_distribution", [{}])[0].get("name", None)
                if parsed_dict.get("source_distribution")
                else None
            ),
        }
        uploaded_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"

        with self._conn() as conn:
            self._clear_all_active(conn)
            cur = conn.execute(
                """
                INSERT INTO uploads (
                    filename_original, filename_stored, file_hash,
                    rows_count, min_date, max_date, uploaded_at,
                    is_active, summary_json, parsed_json_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                """,
                (
                    filename_original,
                    stored_xlsx,
                    file_hash,
                    rows_count,
                    min_date,
                    max_date,
                    uploaded_at,
                    json.dumps(summary, ensure_ascii=False),
                    str(stored_json),
                ),
            )
            conn.commit()
            new_id = cur.lastrowid

            row = conn.execute("SELECT * FROM uploads WHERE id = ?", (new_id,)).fetchone()
            return self._row_to_record(row)

    def list_uploads(self, limit: int = 50) -> List[UploadRecord]:
        db_results: List[UploadRecord] = []
        try:
            with self._conn() as conn:
                rows = conn.execute(
                    "SELECT * FROM uploads ORDER BY uploaded_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
                db_results = [self._row_to_record(r) for r in rows]
        except Exception:
            db_results = []
        bundled = self._build_bundled_virtual_record()
        if bundled:
            if db_results:
                ids = {r.id for r in db_results}
                if bundled.id not in ids:
                    db_results.insert(0, bundled)
            else:
                db_results = [bundled]
        return db_results

    def _build_bundled_virtual_record(self) -> Optional[UploadRecord]:
        if self._bundled_record_cache is not None:
            return self._bundled_record_cache
        json_path: Optional[Path] = None
        if config.SAMPLE_BUNDLED_JSON:
            candidate = Path(config.SAMPLE_BUNDLED_JSON)
            if candidate.exists():
                json_path = candidate
            else:
                cand2 = ASSETS_DIR / config.SAMPLE_BUNDLED_JSON
                if cand2.exists():
                    json_path = cand2
        if not json_path and ASSETS_DIR.exists():
            jsons = sorted(ASSETS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)
            if jsons:
                json_path = jsons[0]
        if not json_path or not json_path.exists():
            return None
        try:
            parsed = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception:
            return None
        md = parsed.get("metadata") or {}
        md2 = parsed.get("overview_kpi") or {}
        rows_count = int(md.get("rows_count") or 0)
        min_date = md.get("min_date") or None
        max_date = md.get("max_date") or None
        try:
            uploaded_at = md.get("uploaded_at") or md.get("parsed_at") or datetime.utcfromtimestamp(json_path.stat().st_mtime).isoformat(timespec="seconds") + "Z"
        except Exception:
            uploaded_at = "2026-01-01T00:00:00Z"
        xlsx_cand = ASSETS_DIR / (json_path.stem + ".xlsx")
        if xlsx_cand.exists():
            try:
                fhash = self._hash_file(xlsx_cand)
            except Exception:
                fhash = "bundled-" + json_path.stem[:16]
        else:
            fhash = "bundled-" + json_path.stem[:16]
        summary = {
            "total_mentions": rows_count,
            "pct_positive": md2.get("pct_positive", 0),
            "pct_negative": md2.get("pct_negative", 0),
            "pct_neutral": md2.get("pct_neutral", 0),
            "sentiment_composite": md2.get("sentiment_composite", 0),
            "total_reach": md2.get("total_reach_sum", 0),
            "top_source": (
                parsed.get("source_distribution", [{}])[0].get("name", None)
                if parsed.get("source_distribution")
                else None
            ),
        }
        rec = UploadRecord(
            id=VIRTUAL_BUNDLED_RECORD_ID,
            filename_original=(json_path.stem + ".xlsx"),
            filename_stored=(json_path.stem + ".xlsx"),
            file_hash=fhash,
            rows_count=rows_count,
            min_date=min_date,
            max_date=max_date,
            uploaded_at=uploaded_at,
            is_active=1,
            parsed_json_path=json_path.name,
            summary_json=json.dumps(summary, ensure_ascii=False),
            bundled_virtual=True,
        )
        self._bundled_record_cache = rec
        return rec

    def get_active(self) -> Optional[UploadRecord]:
        db_rec: Optional[UploadRecord] = None
        if self._db_init_ok:
            try:
                with self._conn() as conn:
                    row = conn.execute(
                        "SELECT * FROM uploads WHERE is_active = 1 LIMIT 1"
                    ).fetchone()
                    if row:
                        db_rec = self._row_to_record(row)
            except Exception:
                db_rec = None
        if db_rec:
            return db_rec
        bundled = self._build_bundled_virtual_record()
        if bundled:
            return bundled
        return None

    def get_by_id(self, upload_id: int) -> Optional[UploadRecord]:
        if upload_id == VIRTUAL_BUNDLED_RECORD_ID:
            bundled = self._build_bundled_virtual_record()
            if bundled and bundled.id == upload_id:
                return bundled
        try:
            with self._conn() as conn:
                row = conn.execute(
                    "SELECT * FROM uploads WHERE id = ?", (upload_id,)
                ).fetchone()
                if row:
                    return self._row_to_record(row)
        except Exception:
            pass
        bundled = self._build_bundled_virtual_record()
        if bundled and bundled.id == upload_id:
            return bundled
        return None

    def set_active(self, upload_id: int) -> bool:
        if upload_id == VIRTUAL_BUNDLED_RECORD_ID:
            return True
        try:
            with self._conn() as conn:
                exists = conn.execute(
                    "SELECT 1 FROM uploads WHERE id = ?", (upload_id,)
                ).fetchone()
                if not exists:
                    return False
                self._clear_all_active(conn)
                conn.execute(
                    "UPDATE uploads SET is_active = 1 WHERE id = ?", (upload_id,)
                )
                conn.commit()
                return True
        except Exception:
            return False

    def delete_upload(self, upload_id: int) -> bool:
        if upload_id == VIRTUAL_BUNDLED_RECORD_ID:
            return True
        rec = self.get_by_id(upload_id)
        if not rec:
            return False
        try:
            xlsx_path = config.UPLOAD_DIR / rec.filename_stored
            json_path = config.PARSED_DIR / rec.parsed_json_path
            if xlsx_path.exists():
                xlsx_path.unlink()
            if json_path.exists():
                json_path.unlink()
        except Exception:
            pass
        try:
            with self._conn() as conn:
                conn.execute("DELETE FROM uploads WHERE id = ?", (upload_id,))
                conn.commit()
        except Exception:
            return False
        return True

    def reparse_upload(
        self, upload_id: int, parser_func: Callable[[Path], Dict[str, Any]]
    ) -> Optional[UploadRecord]:
        rec = self.get_by_id(upload_id)
        if not rec:
            return None
        xlsx_path = config.UPLOAD_DIR / rec.filename_stored
        if not xlsx_path.exists():
            fallback = ASSETS_DIR / rec.filename_stored
            if fallback.exists():
                xlsx_path = fallback
        if not xlsx_path.exists():
            return None
        parsed = parser_func(xlsx_path)
        json_path = config.PARSED_DIR / rec.parsed_json_path
        try:
            json_path.parent.mkdir(parents=True, exist_ok=True)
            json_path.write_text(
                json.dumps(parsed, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )
        except Exception:
            pass
        meta = parsed.get("metadata", {})
        rows_count = meta.get("rows_count", rec.rows_count)
        min_date = meta.get("min_date", rec.min_date)
        max_date = meta.get("max_date", rec.max_date)
        kpi = parsed.get("overview_kpi", {})
        summary = {
            "total_mentions": rows_count,
            "pct_positive": kpi.get("pct_positive", 0),
            "pct_negative": kpi.get("pct_negative", 0),
            "pct_neutral": kpi.get("pct_neutral", 0),
            "sentiment_composite": kpi.get("sentiment_composite", 0),
            "total_reach": kpi.get("total_reach_sum", 0),
            "top_source": (
                parsed.get("source_distribution", [{}])[0].get("name", None)
                if parsed.get("source_distribution")
                else None
            ),
        }
        try:
            with self._conn() as conn:
                conn.execute(
                    """
                    UPDATE uploads
                    SET rows_count = ?, min_date = ?, max_date = ?, summary_json = ?
                    WHERE id = ?
                    """,
                    (
                        rows_count,
                        min_date,
                        max_date,
                        json.dumps(summary, ensure_ascii=False),
                        upload_id,
                    ),
                )
                conn.commit()
        except Exception:
            pass
        return self.get_by_id(upload_id)

    def load_parsed_json(self, upload_id: int) -> Optional[Dict[str, Any]]:
        rec = self.get_by_id(upload_id)
        if not rec:
            return None
        if rec.bundled_virtual:
            json_path = ASSETS_DIR / rec.parsed_json_path
            if json_path.exists():
                try:
                    return json.loads(json_path.read_text(encoding="utf-8"))
                except Exception:
                    return None
            return None
        search_paths: List[Path] = []
        search_paths.append(config.PARSED_DIR / rec.parsed_json_path)
        search_paths.append(ASSETS_DIR / rec.parsed_json_path)
        if rec.parsed_json_path and not rec.parsed_json_path.startswith(str(config.PARSED_DIR)) and "/" in rec.parsed_json_path:
            search_paths.append(Path(rec.parsed_json_path))
        bare = Path(rec.parsed_json_path).name
        for try_dir in (
            ASSETS_DIR,
            BASE_DIR / "data_parsed",
            BASE_DIR / "uploads",
            BASE_DIR,
            config.PARSED_DIR,
        ):
            search_paths.append(try_dir / rec.parsed_json_path)
            search_paths.append(try_dir / bare)
        json_path: Optional[Path] = None
        for p in search_paths:
            try:
                if p and p.exists():
                    json_path = p
                    break
            except Exception:
                continue
        if not json_path:
            return None
        try:
            raw = json_path.read_text(encoding="utf-8")
            return json.loads(raw)
        except Exception:
            return None

    @staticmethod
    def _hash_file(path: Path, chunk: int = 65536) -> str:
        h = hashlib.md5()
        with open(path, "rb") as f:
            while True:
                b = f.read(chunk)
                if not b:
                    break
                h.update(b)
        return h.hexdigest()


def record_to_dict(rec: UploadRecord) -> Dict[str, Any]:
    d = asdict(rec)
    d.pop("_summary_cache", None)
    d.pop("bundled_virtual", None)
    d["summary"] = rec.summary
    d["filename"] = d.get("filename_original")
    d["created_at"] = d.get("uploaded_at")
    d["date_range_min"] = d.get("min_date")
    d["date_range_max"] = d.get("max_date")
    d["status"] = "Ready"
    try:
        p = config.UPLOAD_DIR / rec.filename_stored
        if not p.exists():
            p = ASSETS_DIR / rec.filename_stored
        d["file_size"] = int(p.stat().st_size) if p.exists() else 0
    except Exception:
        d["file_size"] = 0
    return d
