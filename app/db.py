import sqlite3
import json
import uuid
import hashlib
import shutil
import os
from pathlib import Path
from typing import Optional, List, Any, Dict, Callable, Union, Tuple
from dataclasses import dataclass, asdict, field
from datetime import datetime

from . import config

try:
    import psycopg2
    import psycopg2.extras
    _HAS_PSYCOPG2 = True
except Exception:
    psycopg2 = None
    _HAS_PSYCOPG2 = False


ASSETS_DIR = config.ASSETS_DIR
BASE_DIR = config.BASE_DIR
VIRTUAL_BUNDLED_RECORD_ID = 9999
VIRTUAL_TEMP_UPLOAD_ID_START = 8888


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
    temp_virtual: bool = False

    @property
    def summary(self) -> Dict[str, Any]:
        if self._summary_cache is None:
            try:
                self._summary_cache = json.loads(self.summary_json)
            except Exception:
                self._summary_cache = {}
        return self._summary_cache


class UploadRepository:
    _shared_temp_uploads: Dict[int, UploadRecord] = {}
    _shared_active_temp_id: Optional[int] = None

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or config.DB_PATH
        try:
            self.init_db()
            self._db_init_ok = True
        except Exception:
            self._db_init_ok = False
        self._bundled_record_cache: Optional[UploadRecord] = None
        self._temp_uploads = UploadRepository._shared_temp_uploads
        self._active_temp_id_ref = UploadRepository._shared_active_temp_id

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

    @staticmethod
    def _is_readonly_error(e: Exception) -> bool:
        msg = str(e).lower()
        return (
            "readonly" in msg
            or "read-only" in msg
            or "read only" in msg
            or "attempt to write a readonly database" in msg
            or "unable to open database file" in msg
            or "permission denied" in msg
        )

    def init_db(self) -> None:
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
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

    def _make_temp_upload_record(
        self,
        filename_original: str,
        stored_xlsx_name: str,
        stored_json_name: str,
        file_hash: str,
        parsed_dict: Dict[str, Any],
        rows_count: int,
        min_date: Optional[str],
        max_date: Optional[str],
    ) -> UploadRecord:
        existing_by_hash = {r.file_hash: r for r in self._temp_uploads.values()}
        if file_hash in existing_by_hash:
            rec = existing_by_hash[file_hash]
            self._active_temp_id_ref = rec.id
            for r in self._temp_uploads.values():
                r.is_active = 1 if r.id == rec.id else 0
            return rec
        next_id = VIRTUAL_TEMP_UPLOAD_ID_START
        used_ids = set(self._temp_uploads.keys())
        while next_id in used_ids:
            next_id += 1
        meta = parsed_dict.get("overview_kpi", {}) or {}
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
        rec = UploadRecord(
            id=next_id,
            filename_original=filename_original,
            filename_stored=stored_xlsx_name,
            file_hash=file_hash,
            rows_count=rows_count,
            min_date=min_date,
            max_date=max_date,
            uploaded_at=uploaded_at,
            is_active=1,
            parsed_json_path=stored_json_name,
            summary_json=json.dumps(summary, ensure_ascii=False),
            temp_virtual=True,
        )
        for r in self._temp_uploads.values():
            r.is_active = 0
        self._temp_uploads[rec.id] = rec
        self._active_temp_id_ref = rec.id
        return rec

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

        try:
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
        except Exception as e:
            if not self._is_readonly_error(e):
                raise

        stored_uuid = str(uuid.uuid4())
        stored_xlsx = f"{stored_uuid}.xlsx"
        stored_json = f"{stored_uuid}.json"
        stored_path = config.UPLOAD_DIR / stored_xlsx
        json_path = config.PARSED_DIR / stored_json

        try:
            config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
            config.PARSED_DIR.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        try:
            shutil.copyfile(str(temp_file_path), str(stored_path))
        except Exception:
            try:
                stored_path.write_bytes(temp_file_path.read_bytes())
            except Exception:
                pass
        try:
            json_path.write_text(
                json.dumps(parsed_dict, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )
        except Exception:
            pass

        meta = parsed_dict.get("overview_kpi", {}) or {}
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

        try:
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
        except Exception as e:
            if not self._is_readonly_error(e):
                raise
            return self._make_temp_upload_record(
                filename_original=filename_original,
                stored_xlsx_name=stored_xlsx,
                stored_json_name=stored_json,
                file_hash=file_hash,
                parsed_dict=parsed_dict,
                rows_count=rows_count,
                min_date=min_date,
                max_date=max_date,
            )

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
        temp_list = sorted(self._temp_uploads.values(), key=lambda r: r.uploaded_at, reverse=True)
        if temp_list:
            db_ids = {r.id for r in db_results}
            db_results = [r for r in temp_list if r.id not in db_ids] + db_results
        bundled = self._build_bundled_virtual_record()
        if bundled:
            if db_results:
                ids = {r.id for r in db_results}
                if bundled.id not in ids:
                    db_results.insert(0, bundled)
            else:
                db_results = [bundled]
        return db_results[:limit]

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
        if self._active_temp_id_ref is not None and self._active_temp_id_ref in self._temp_uploads:
            return self._temp_uploads[self._active_temp_id_ref]
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
        if upload_id in self._temp_uploads:
            return self._temp_uploads[upload_id]
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

    def _clear_all_active_in_memory(self) -> None:
        for r in self._temp_uploads.values():
            r.is_active = 0
        if self._active_temp_id_ref in self._temp_uploads:
            self._active_temp_id_ref = None

    def set_active(self, upload_id: int) -> bool:
        if upload_id == VIRTUAL_BUNDLED_RECORD_ID:
            self._clear_all_active_in_memory()
            return True
        if upload_id in self._temp_uploads:
            for r in self._temp_uploads.values():
                r.is_active = 1 if r.id == upload_id else 0
            self._active_temp_id_ref = upload_id
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
                self._active_temp_id_ref = None
                return True
        except Exception as e:
            if not self._is_readonly_error(e):
                raise
            return False

    def delete_upload(self, upload_id: int) -> bool:
        if upload_id == VIRTUAL_BUNDLED_RECORD_ID:
            return True
        if upload_id in self._temp_uploads:
            rec = self._temp_uploads.pop(upload_id)
            try:
                xlsx_path = config.UPLOAD_DIR / rec.filename_stored
                json_path = config.PARSED_DIR / rec.parsed_json_path
                if xlsx_path.exists():
                    xlsx_path.unlink()
                if json_path.exists():
                    json_path.unlink()
            except Exception:
                pass
            if self._active_temp_id_ref == upload_id:
                self._active_temp_id_ref = None
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
                return True
        except Exception as e:
            if not self._is_readonly_error(e):
                raise
            return False

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


class PostgresStorageError(Exception):
    pass


class PostgresUploadsRepository:
    POSTGRES_SCHEMA_SQL = """
        CREATE TABLE IF NOT EXISTS uploads (
            id SERIAL PRIMARY KEY,
            filename_original TEXT NOT NULL,
            filename_stored TEXT NOT NULL,
            file_hash TEXT NOT NULL UNIQUE,
            rows_count INTEGER NOT NULL DEFAULT 0,
            min_date TEXT,
            max_date TEXT,
            uploaded_at TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 0,
            summary_json TEXT NOT NULL DEFAULT '{}',
            parsed_json_path TEXT NOT NULL,
            tracked_keywords_json TEXT,
            blob_xlsx_url TEXT NOT NULL,
            blob_json_url TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_uploads_active ON uploads(is_active);
        CREATE INDEX IF NOT EXISTS idx_uploads_uploaded_at ON uploads(uploaded_at DESC);
    """

    def __init__(self):
        if not _HAS_PSYCOPG2:
            raise PostgresStorageError(
                "psycopg2-binary tidak terinstall. Jalankan pip install psycopg2-binary"
            )
        if not config.POSTGRES_URL:
            raise PostgresStorageError(
                "POSTGRES_URL environment variable tidak tersedia. "
                "Enable Vercel Postgres Storage untuk permanent upload mode."
            )
        self._url = config.POSTGRES_URL
        try:
            self.init_db()
            self._db_init_ok = True
        except Exception as e:
            self._db_init_ok = False
            raise PostgresStorageError(f"Init Postgres gagal: {e}") from None
        try:
            from .blob_storage import BlobStorageClient
            self._blob = BlobStorageClient()
        except Exception as e:
            raise PostgresStorageError(f"Init BlobStorage gagal: {e}") from None

    def _connect(self):
        try:
            c = psycopg2.connect(self._url, connect_timeout=15)
            c.autocommit = False
            return c
        except Exception as e:
            raise PostgresStorageError(
                f"Tidak bisa konek ke Postgres (timeout/kredensial salah). Cek POSTGRES_URL env: {type(e).__name__}"
            ) from None

    def init_db(self) -> None:
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(self.POSTGRES_SCHEMA_SQL)
                conn.commit()
        except PostgresStorageError:
            raise
        except Exception as e:
            raise PostgresStorageError(f"Init Postgres table gagal: {e}") from None

    def _row_to_record(self, row: Tuple) -> UploadRecord:
        cols = [
            "id","filename_original","filename_stored","file_hash","rows_count","min_date","max_date",
            "uploaded_at","is_active","summary_json","parsed_json_path","tracked_keywords_json",
            "blob_xlsx_url","blob_json_url"
        ]
        d = dict(zip(cols, row))
        blob_xlsx = d.pop("blob_xlsx_url", None)
        blob_json = d.pop("blob_json_url", None)
        d.pop("tracked_keywords_json", None)
        rec = UploadRecord(**{
            k: (d[k] if d[k] is not None else "")
            for k in ["id","filename_original","filename_stored","file_hash","rows_count","min_date","max_date","uploaded_at","is_active","summary_json","parsed_json_path"]
        })
        rec.blob_xlsx_url = blob_xlsx
        rec.blob_json_url = blob_json
        return rec

    def create_upload(
        self,
        filename_original: str,
        filename_stored: str,
        parsed_json_path: str,
        file_hash: str,
        rows_count: int,
        min_date: Optional[str],
        max_date: Optional[str],
        uploaded_at: str,
        blob_xlsx_url: str,
        blob_json_url: str,
        summary_dict: Optional[Dict[str, Any]] = None,
        tracked_keywords_json: Optional[str] = None,
        auto_set_active: bool = True,
    ) -> UploadRecord:
        summary_json = json.dumps(summary_dict or {}, ensure_ascii=False)
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    if auto_set_active:
                        cur.execute("UPDATE uploads SET is_active = 0 WHERE is_active = 1")
                    cur.execute(
                        """
                        INSERT INTO uploads
                          (filename_original, filename_stored, file_hash, rows_count, min_date, max_date, uploaded_at, is_active, summary_json, parsed_json_path, tracked_keywords_json, blob_xlsx_url, blob_json_url)
                        VALUES
                          (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id, filename_original, filename_stored, file_hash, rows_count, min_date, max_date, uploaded_at, is_active, summary_json, parsed_json_path, tracked_keywords_json, blob_xlsx_url, blob_json_url
                        """,
                        (
                            filename_original, filename_stored, file_hash, int(rows_count or 0),
                            min_date, max_date, uploaded_at, 1 if auto_set_active else 0,
                            summary_json, parsed_json_path, tracked_keywords_json or "[]",
                            blob_xlsx_url, blob_json_url,
                        ),
                    )
                    row = cur.fetchone()
                conn.commit()
            if not row:
                raise PostgresStorageError("Insert Postgres return kosong")
            return self._row_to_record(row)
        except PostgresStorageError:
            raise
        except Exception as e:
            if isinstance(e, psycopg2.IntegrityError) and "file_hash" in str(e).lower():
                try:
                    return self._get_by_hash(file_hash)
                except Exception as e2:
                    raise PostgresStorageError(f"Duplicate file hash tapi gagal load: {e2}") from None
            raise PostgresStorageError(f"Insert Postgres gagal: {type(e).__name__}: {e}") from None

    def _get_by_hash(self, file_hash: str) -> UploadRecord:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, filename_original, filename_stored, file_hash, rows_count, min_date, max_date, uploaded_at, is_active, summary_json, parsed_json_path, tracked_keywords_json, blob_xlsx_url, blob_json_url FROM uploads WHERE file_hash = %s LIMIT 1",
                    (file_hash,),
                )
                row = cur.fetchone()
        if not row:
            raise PostgresStorageError("Not found by hash")
        return self._row_to_record(row)

    def list_uploads(self, limit: int = 25) -> List[UploadRecord]:
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT id, filename_original, filename_stored, file_hash, rows_count, min_date, max_date, uploaded_at, is_active, summary_json, parsed_json_path, tracked_keywords_json, blob_xlsx_url, blob_json_url FROM uploads ORDER BY uploaded_at DESC LIMIT %s",
                        (int(max(limit, 1)),),
                    )
                    rows = cur.fetchall()
        except PostgresStorageError:
            raise
        except Exception as e:
            raise PostgresStorageError(f"List uploads Postgres gagal: {type(e).__name__}") from None
        return [self._row_to_record(r) for r in (rows or [])]

    def get_active(self) -> Optional[UploadRecord]:
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT id, filename_original, filename_stored, file_hash, rows_count, min_date, max_date, uploaded_at, is_active, summary_json, parsed_json_path, tracked_keywords_json, blob_xlsx_url, blob_json_url FROM uploads WHERE is_active = 1 ORDER BY uploaded_at DESC LIMIT 1"
                    )
                    row = cur.fetchone()
        except PostgresStorageError:
            raise
        except Exception as e:
            raise PostgresStorageError(f"Get active Postgres gagal: {type(e).__name__}") from None
        if not row:
            return None
        return self._row_to_record(row)

    def get_by_id(self, upload_id: int) -> Optional[UploadRecord]:
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT id, filename_original, filename_stored, file_hash, rows_count, min_date, max_date, uploaded_at, is_active, summary_json, parsed_json_path, tracked_keywords_json, blob_xlsx_url, blob_json_url FROM uploads WHERE id = %s LIMIT 1",
                        (int(upload_id),),
                    )
                    row = cur.fetchone()
        except PostgresStorageError:
            raise
        except Exception as e:
            raise PostgresStorageError(f"Get by id Postgres gagal: {type(e).__name__}") from None
        if not row:
            return None
        return self._row_to_record(row)

    def set_active(self, upload_id: int) -> bool:
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("UPDATE uploads SET is_active = 0 WHERE is_active = 1")
                    cur.execute("UPDATE uploads SET is_active = 1 WHERE id = %s", (int(upload_id),))
                    ok = cur.rowcount > 0
                conn.commit()
            return bool(ok)
        except PostgresStorageError:
            raise
        except Exception as e:
            raise PostgresStorageError(f"Set active Postgres gagal: {type(e).__name__}") from None

    def delete_upload(self, upload_id: int) -> bool:
        rec = self.get_by_id(upload_id)
        if not rec:
            return False
        try:
            urls = [u for u in (getattr(rec, "blob_xlsx_url", None), getattr(rec, "blob_json_url", None)) if isinstance(u, str) and u.strip()]
            if urls:
                try:
                    self._blob.delete(urls)
                except Exception:
                    pass
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM uploads WHERE id = %s", (int(upload_id),))
                    ok = cur.rowcount > 0
                conn.commit()
            return bool(ok)
        except PostgresStorageError:
            raise
        except Exception as e:
            raise PostgresStorageError(f"Delete Postgres gagal: {type(e).__name__}") from None

    def load_parsed_json(self, upload_id: int) -> Optional[Dict[str, Any]]:
        rec = self.get_by_id(upload_id)
        if not rec:
            return None
        blob_url = getattr(rec, "blob_json_url", None)
        if blob_url:
            try:
                raw_bytes = self._blob.download_bytes(blob_url)
                try:
                    return json.loads(raw_bytes.decode("utf-8"))
                except Exception:
                    try:
                        return json.loads(raw_bytes.decode("utf-8", errors="replace"))
                    except Exception:
                        return None
            except Exception:
                return None
        fallback = UploadRepository(db_path=config.DB_PATH)
        return fallback.load_parsed_json(upload_id)


_singleton_repo_ref: Dict[str, Any] = {"sqlite": None, "postgres": None}


def get_upload_repository() -> Union[UploadRepository, PostgresUploadsRepository]:
    if config.IS_PERMANENT_MODE and _HAS_PSYCOPG2:
        if _singleton_repo_ref["postgres"] is None:
            try:
                _singleton_repo_ref["postgres"] = PostgresUploadsRepository()
            except Exception:
                _singleton_repo_ref["postgres"] = False
        inst = _singleton_repo_ref["postgres"]
        if isinstance(inst, PostgresUploadsRepository):
            return inst
    if _singleton_repo_ref["sqlite"] is None:
        _singleton_repo_ref["sqlite"] = UploadRepository()
    return _singleton_repo_ref["sqlite"]


def record_to_dict(rec: UploadRecord) -> Dict[str, Any]:
    d = asdict(rec)
    d.pop("_summary_cache", None)
    d.pop("bundled_virtual", None)
    d.pop("temp_virtual", None)
    blob_xlsx = getattr(rec, "blob_xlsx_url", None)
    blob_json = getattr(rec, "blob_json_url", None)
    if blob_xlsx:
        d["blob_xlsx_url"] = blob_xlsx
    if blob_json:
        d["blob_json_url"] = blob_json
    d["summary"] = rec.summary
    d["filename"] = d.get("filename_original")
    d["created_at"] = d.get("uploaded_at")
    d["date_range_min"] = d.get("min_date")
    d["date_range_max"] = d.get("max_date")
    if getattr(rec, "temp_virtual", False):
        d["status"] = "Demo (Temp /tmp)"
        d["persistent"] = False
    elif getattr(rec, "bundled_virtual", False):
        d["status"] = "Bundled Sample"
        d["persistent"] = True
    elif blob_json or blob_xlsx or isinstance(rec.__class__, type) and rec.__class__.__name__ == "PostgresUploadsRecordStub":
        d["status"] = "Ready (Permanent)"
        d["persistent"] = True
    elif getattr(rec, "blob_json_url", None) or getattr(rec, "blob_xlsx_url", None):
        d["status"] = "Ready (Permanent)"
        d["persistent"] = True
    else:
        try:
            from .blob_storage import BlobStorageError as _BSE
        except Exception:
            _BSE = type(None)
        if isinstance(globals().get("__permanent_marker__", None), type(True)) and rec.id >= 1:
            d["status"] = "Ready (Permanent)"
            d["persistent"] = True
        else:
            d["status"] = "Ready"
            d["persistent"] = True
    for attr in ("blob_xlsx_url", "blob_json_url"):
        if getattr(rec, attr, None) is not None:
            d["status"] = "Ready (Permanent)"
            d["persistent"] = True
            break
    try:
        p = config.UPLOAD_DIR / rec.filename_stored
        if not p.exists():
            p = ASSETS_DIR / rec.filename_stored
        if not p.exists() and getattr(rec, "temp_virtual", False):
            p = config.PARSED_DIR / rec.parsed_json_path
        d["file_size"] = int(p.stat().st_size) if p and p.exists() else 0
        if d["file_size"] == 0 and getattr(rec, "blob_xlsx_url", None):
            d["file_size"] = int(d.get("file_size") or 0)
    except Exception:
        d["file_size"] = 0
    return d

