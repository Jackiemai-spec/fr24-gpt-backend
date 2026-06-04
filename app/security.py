import hmac
import hashlib
import os
import time
from fastapi import Header, HTTPException, Query


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    expected = os.environ.get("BACKEND_API_KEY")
    if not expected:
        raise HTTPException(status_code=500, detail="BACKEND_API_KEY is not configured")
    if not x_api_key or not hmac.compare_digest(x_api_key, expected):
        raise HTTPException(status_code=401, detail="Unauthorized")


def sign_download(report_id: str, expires: int) -> str:
    secret = os.environ.get("DOWNLOAD_SIGNING_SECRET")
    if not secret:
        raise HTTPException(status_code=500, detail="DOWNLOAD_SIGNING_SECRET is not configured")
    payload = f"{report_id}:{expires}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def validate_download_signature(
    report_id: str,
    expires: int = Query(...),
    signature: str = Query(...),
) -> None:
    if int(time.time()) > expires:
        raise HTTPException(status_code=403, detail="Download link has expired")
    expected = sign_download(report_id, expires)
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=403, detail="Invalid download signature")
