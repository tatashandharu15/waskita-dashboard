import json
import tempfile
from pathlib import Path
from typing import Dict, Any

from fastapi import APIRouter, Request, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse

from . import config
from .db import record_to_dict
from .parser import parse_excel_file, ParseError


router = APIRouter(tags=["admin"])


def validate_secret_on_router(request: Request) -> None:
    secret = request.path_params.get("secret")
    if secret != config.ADMIN_SECRET:
        raise HTTPException(status_code=404, detail="Not Found")


@router.get("/admin/{secret}/api/uploads")
async def admin_list_uploads(request: Request, secret: str):
    validate_secret_on_router(request)
    repo = request.app.state.repo
    records = repo.list_uploads(limit=100)
    return JSONResponse({"uploads": [record_to_dict(r) for r in records]})


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
            tmp_path = Path(tmp.name)

        try:
            parsed = parse_excel_file(tmp_path)
        except ParseError as e:
            raise HTTPException(status_code=400, detail=f"Parse error: {e.msg}")
        except Exception as e:
            raise HTTPException(
                status_code=400, detail=f"Failed to parse Excel file: {type(e).__name__}"
            )

        repo = request.app.state.repo
        meta = parsed.get("metadata", {})
        rec = repo.create_upload(
            filename_original=file.filename,
            temp_file_path=tmp_path,
            parsed_dict=parsed,
            rows_count=meta.get("rows_count", 0),
            min_date=meta.get("min_date"),
            max_date=meta.get("max_date"),
        )
        return JSONResponse({"ok": True, "upload": record_to_dict(rec)})
    finally:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


@router.post("/admin/{secret}/api/uploads/{upload_id}/set-active")
async def admin_set_active(request: Request, secret: str, upload_id: int):
    validate_secret_on_router(request)
    repo = request.app.state.repo
    changed = repo.set_active(upload_id)
    if not changed:
        raise HTTPException(status_code=404, detail="Upload not found")
    return JSONResponse({"ok": True, "now_active_id": upload_id})


@router.delete("/admin/{secret}/api/uploads/{upload_id}")
async def admin_delete_upload(request: Request, secret: str, upload_id: int):
    validate_secret_on_router(request)
    repo = request.app.state.repo
    deleted = repo.delete_upload(upload_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Upload not found")
    return JSONResponse({"ok": True})


@router.post("/admin/{secret}/api/uploads/{upload_id}/reparse")
async def admin_reparse_upload(request: Request, secret: str, upload_id: int):
    validate_secret_on_router(request)
    repo = request.app.state.repo
    rec = repo.get_by_id(upload_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Upload not found")
    xlsx_path = config.UPLOAD_DIR / rec.filename_stored
    if not xlsx_path.exists():
        raise HTTPException(status_code=400, detail="Original xlsx file missing")
    try:
        def parser(p: Path):
            return parse_excel_file(p)
        new_rec = repo.reparse_upload(upload_id, parser)
    except ParseError as e:
        raise HTTPException(status_code=400, detail=f"Parse error: {e.msg}")
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Reparse failed: {type(e).__name__}"
        )
    if not new_rec:
        raise HTTPException(status_code=400, detail="Reparse failed")
    return JSONResponse({"ok": True, "upload": record_to_dict(new_rec)})
