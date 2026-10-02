import json
import tempfile
import uuid
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any

from fastapi import APIRouter, Request, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse

from . import config
from .db import (
    record_to_dict,
    get_upload_repository,
    PostgresStorageError,
    PostgresUploadsRepository,
)
from .blob_storage import BlobStorageClient, BlobStorageError
from .parser import parse_excel_file, ParseError


router = APIRouter(tags=["admin"])


def validate_secret_on_router(request: Request) -> None:
    secret = request.path_params.get("secret")
    if secret != config.ADMIN_SECRET:
        raise HTTPException(status_code=404, detail="Not Found")


@router.get("/admin/{secret}/api/uploads")
async def admin_list_uploads(request: Request, secret: str):
    validate_secret_on_router(request)
    try:
        repo = request.app.state.repo
        records = repo.list_uploads(limit=100)
        return JSONResponse({"uploads": [record_to_dict(r) for r in records]})
    except (PostgresStorageError, BlobStorageError):
        raise HTTPException(
            status_code=503,
            detail="Storage Vercel sementara tidak tersedia, coba beberapa saat lagi"
        )


@router.post("/admin/{secret}/api/upload")
async def admin_upload_file(
    request: Request,
    secret: str,
    file: UploadFile = File(...),
):
    validate_secret_on_router(request)

    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    allowed_exts = (".xlsx", ".xls")
    ext_ok = any(file.filename.lower().endswith(e) for e in allowed_exts)
    if not ext_ok:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_exts)}",
        )

    size_bytes = 0
    max_bytes = config.MAX_UPLOAD_MB * 1024 * 1024
    tmp_path: Path | None = None
    try:
        file_bytes = bytearray()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            while True:
                chunk = await file.read(1024 * 64)
                if not chunk:
                    break
                size_bytes += len(chunk)
                if size_bytes > max_bytes:
                    tmp.close()
                    Path(tmp.name).unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large. Max {config.MAX_UPLOAD_MB} MB",
                    )
                tmp.write(chunk)
                file_bytes.extend(chunk)
            tmp_path = Path(tmp.name)

        try:
            parsed = parse_excel_file(tmp_path)
        except ParseError as e:
            raise HTTPException(status_code=400, detail=f"Parse error: {e.msg}")
        except Exception as e:
            raise HTTPException(
                status_code=400, detail=f"Failed to parse Excel file: {type(e).__name__}"
            )

        try:
            repo = request.app.state.repo
            meta = parsed.get("metadata", {})

            is_permanent = config.IS_PERMANENT_MODE and isinstance(repo, PostgresUploadsRepository)

            if is_permanent:
                raw_bytes = bytes(file_bytes)
                sha256_hash = hashlib.sha256(raw_bytes).hexdigest()[:16]
                uploaded_at = datetime.now(timezone.utc).isoformat(timespec="seconds") + "Z"

                stored_uuid = str(uuid.uuid4())
                stored_xlsx = f"{stored_uuid}.xlsx"
                stored_json = f"{stored_uuid}.json"

                blob_client = BlobStorageClient()
                xlsx_pathname, json_pathname = blob_client.generate_upload_pathnames(stored_uuid)

                xlsx_resp = blob_client.upload_bytes(
                    xlsx_pathname,
                    raw_bytes,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

                json_bytes = json.dumps(parsed, ensure_ascii=False).encode("utf-8")
                json_resp = blob_client.upload_bytes(
                    json_pathname,
                    json_bytes,
                    "application/json",
                )

                summary_dict = parsed.get("overview_kpi", {}) or {}
                keywords = parsed.get("tracked_keywords", []) or []
                tracked_json = json.dumps(keywords, ensure_ascii=False)

                rec = repo.create_upload(
                    filename_original=file.filename,
                    filename_stored=stored_xlsx,
                    parsed_json_path=stored_json,
                    file_hash=sha256_hash,
                    rows_count=meta.get("rows_count", 0),
                    min_date=meta.get("min_date"),
                    max_date=meta.get("max_date"),
                    uploaded_at=uploaded_at,
                    blob_xlsx_url=xlsx_resp["url"],
                    blob_json_url=json_resp["url"],
                    summary_dict=summary_dict,
                    tracked_keywords_json=tracked_json,
                    auto_set_active=True,
                )
                return JSONResponse({"ok": True, "upload": record_to_dict(rec)})
            else:
                rec = repo.create_upload(
                    filename_original=file.filename,
                    temp_file_path=tmp_path,
                    parsed_dict=parsed,
                    rows_count=meta.get("rows_count", 0),
                    min_date=meta.get("min_date"),
                    max_date=meta.get("max_date"),
                )
                return JSONResponse({"ok": True, "upload": record_to_dict(rec)})
        except (PostgresStorageError, BlobStorageError):
            raise HTTPException(
                status_code=503,
                detail="Storage Vercel sementara tidak tersedia, coba beberapa saat lagi"
            )
    finally:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


@router.post("/admin/{secret}/api/uploads/{upload_id}/set-active")
async def admin_set_active(request: Request, secret: str, upload_id: int):
    validate_secret_on_router(request)
    try:
        repo = request.app.state.repo
        changed = repo.set_active(upload_id)
        if not changed:
            raise HTTPException(status_code=404, detail="Upload not found")
        return JSONResponse({"ok": True, "now_active_id": upload_id})
    except (PostgresStorageError, BlobStorageError):
        raise HTTPException(
            status_code=503,
            detail="Storage Vercel sementara tidak tersedia, coba beberapa saat lagi"
        )


@router.delete("/admin/{secret}/api/uploads/{upload_id}")
async def admin_delete_upload(request: Request, secret: str, upload_id: int):
    validate_secret_on_router(request)
    try:
        repo = request.app.state.repo
        deleted = repo.delete_upload(upload_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Upload not found")
        return JSONResponse({"ok": True})
    except (PostgresStorageError, BlobStorageError):
        raise HTTPException(
            status_code=503,
            detail="Storage Vercel sementara tidak tersedia, coba beberapa saat lagi"
        )


@router.post("/admin/{secret}/api/uploads/{upload_id}/reparse")
async def admin_reparse_upload(request: Request, secret: str, upload_id: int):
    validate_secret_on_router(request)
    try:
        repo = request.app.state.repo
        rec = repo.get_by_id(upload_id)
        if not rec:
            raise HTTPException(status_code=404, detail="Upload not found")

        tmp_reparse: Path | None = None
        try:
            is_permanent = isinstance(repo, PostgresUploadsRepository)
            if is_permanent:
                blob_xlsx = getattr(rec, "blob_xlsx_url", None)
                if not blob_xlsx:
                    raise HTTPException(status_code=400, detail="Blob xlsx URL missing")
                blob_client = BlobStorageClient()
                xlsx_bytes = blob_client.download_bytes(blob_xlsx)
                with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tf:
                    tf.write(xlsx_bytes)
                    tmp_reparse = Path(tf.name)
            else:
                xlsx_path = config.UPLOAD_DIR / rec.filename_stored
                if not xlsx_path.exists():
                    raise HTTPException(status_code=400, detail="Original xlsx file missing")
                tmp_reparse = xlsx_path

            def parser(p: Path):
                return parse_excel_file(p)

            if is_permanent:
                parsed = parse_excel_file(tmp_reparse)
                json_bytes = json.dumps(parsed, ensure_ascii=False).encode("utf-8")
                blob_json = getattr(rec, "blob_json_url", None)
                if blob_json:
                    try:
                        pathname = f"uploads/{Path(rec.filename_stored).stem}/parsed.json"
                        blob_client = BlobStorageClient()
                        blob_client.upload_bytes(pathname, json_bytes, "application/json")
                    except Exception:
                        pass
                md = parsed.get("metadata", {})
                with repo._connect() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            "UPDATE uploads SET rows_count=%s, min_date=%s, max_date=%s, summary_json=%s WHERE id=%s",
                            (
                                int(md.get("rows_count", 0) or 0),
                                md.get("min_date"),
                                md.get("max_date"),
                                json.dumps(parsed.get("overview_kpi", {}) or {}, ensure_ascii=False),
                                int(upload_id),
                            ),
                        )
                    conn.commit()
                rec = repo.get_by_id(upload_id)
                if not rec:
                    raise HTTPException(status_code=400, detail="Reparse failed")
                return JSONResponse({"ok": True, "upload": record_to_dict(rec)})
            else:
                new_rec = repo.reparse_upload(upload_id, parser)
                if not new_rec:
                    raise HTTPException(status_code=400, detail="Reparse failed")
                return JSONResponse({"ok": True, "upload": record_to_dict(new_rec)})
        finally:
            if tmp_reparse and tmp_reparse != config.UPLOAD_DIR / rec.filename_stored and tmp_reparse.exists():
                tmp_reparse.unlink(missing_ok=True)
    except ParseError as e:
        raise HTTPException(status_code=400, detail=f"Parse error: {e.msg}")
    except (PostgresStorageError, BlobStorageError):
        raise HTTPException(
            status_code=503,
            detail="Storage Vercel sementara tidak tersedia, coba beberapa saat lagi"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Reparse failed: {type(e).__name__}"
        )
