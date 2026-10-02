import json
from typing import Tuple, Optional
from pathlib import Path

import requests

from . import config


class BlobStorageError(Exception):
    pass


def _mask_token(token: Optional[str]) -> str:
    if not token:
        return "<empty>"
    if len(token) <= 8:
        return "***"
    return f"{token[:4]}***{token[-4:]}"


class BlobStorageClient:
    def __init__(self):
        self.api_url = config.BLOB_API_URL.rstrip("/")
        self.token = config.BLOB_READ_WRITE_TOKEN
        if not self.token:
            raise BlobStorageError(
                "BLOB_READ_WRITE_TOKEN tidak tersedia di environment. "
                "Enable Vercel Blob Storage di tab Storage untuk permanent upload mode."
            )
        self.session = requests.Session()

    def _headers(self, extra: Optional[dict] = None) -> dict:
        h = {
            "Authorization": f"Bearer {self.token}",
            "User-Agent": "waskita-analytics/permanent-blob-v1",
        }
        if extra:
            h.update(extra)
        return h

    def generate_upload_pathnames(self, upload_uuid: str) -> Tuple[str, str]:
        safe = upload_uuid.strip().replace("/", "_").replace("\\", "_")
        if not safe:
            raise BlobStorageError("upload_uuid tidak valid")
        return (f"uploads/{safe}/original.xlsx", f"uploads/{safe}/parsed.json")

    def upload_bytes(self, pathname: str, content_bytes: bytes, content_type: str) -> dict:
        if not pathname:
            raise BlobStorageError("pathname kosong")
        url = f"{self.api_url}/{pathname.lstrip('/')}"
        headers = self._headers(
            {
                "Content-Type": content_type or "application/octet-stream",
                "x-vercel-add-random-suffix": "0",
            }
        )
        try:
            resp = self.session.put(url, data=content_bytes, headers=headers, timeout=30)
        except requests.RequestException as e:
            raise BlobStorageError(
                f"Network error upload Blob ({_mask_token(self.token)}): {type(e).__name__}"
            ) from None
        if resp.status_code < 200 or resp.status_code >= 300:
            try:
                info = resp.json()
            except Exception:
                info = {"raw": resp.text[:300]}
            raise BlobStorageError(
                f"Blob upload gagal HTTP {resp.status_code}: {json.dumps(info, ensure_ascii=False)[:300]}"
            )
        try:
            data = resp.json()
        except Exception:
            raise BlobStorageError("Blob upload response bukan JSON valid")
        if not isinstance(data, dict) or "url" not in data:
            raise BlobStorageError(f"Response Blob tidak memiliki field url: {list(data.keys())[:5]}")
        return data

    def delete(self, url_or_pathnames: list) -> bool:
        if not url_or_pathnames:
            return True
        payload = {"urls": list(url_or_pathnames)}
        url = f"{self.api_url}/delete"
        headers = self._headers({"Content-Type": "application/json"})
        try:
            resp = self.session.post(url, json=payload, headers=headers, timeout=25)
        except requests.RequestException as e:
            raise BlobStorageError(
                f"Network error delete Blob ({_mask_token(self.token)}): {type(e).__name__}"
            ) from None
        if resp.status_code == 404:
            return True
        if resp.status_code < 200 or resp.status_code >= 300:
            try:
                info = resp.json()
            except Exception:
                info = {"raw": resp.text[:300]}
            raise BlobStorageError(
                f"Blob delete gagal HTTP {resp.status_code}: {json.dumps(info, ensure_ascii=False)[:300]}"
            )
        return True

    def download_bytes(self, url: str) -> bytes:
        if not url:
            raise BlobStorageError("download url kosong")
        try:
            if url.startswith(self.api_url) or "blob.vercel-storage.com" in url:
                resp = self.session.get(
                    url,
                    headers=self._headers(),
                    timeout=45,
                )
            else:
                resp = self.session.get(url, timeout=45)
        except requests.RequestException as e:
            raise BlobStorageError(
                f"Network error download Blob: {type(e).__name__}"
            ) from None
        if resp.status_code < 200 or resp.status_code >= 300:
            raise BlobStorageError(f"Blob download gagal HTTP {resp.status_code} url={url[:80]}")
        return resp.content
