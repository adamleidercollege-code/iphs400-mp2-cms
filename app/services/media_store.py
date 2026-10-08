"""Upload validation and on-disk storage for Media (#15).

The browser's claimed filename and Content-Type are never trusted: the
actual bytes are sniffed for a real image signature, and the file is saved
under a generated name (never the original filename, a hard constraint).
"""
from __future__ import annotations

import secrets

from app import settings

MAX_SIZE = 5 * 1024 * 1024  # ~5 MB

_SIGNATURES: list[tuple[bytes, str, str]] = [
    (b"\xff\xd8\xff", "image/jpeg", ".jpg"),
    (b"\x89PNG\r\n\x1a\n", "image/png", ".png"),
]


class UploadRejected(Exception):
    """Raised for an invalid upload — not a real image, or too large."""


def _sniff(data: bytes) -> tuple[str, str]:
    for signature, content_type, ext in _SIGNATURES:
        if data.startswith(signature):
            return content_type, ext
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp", ".webp"
    raise UploadRejected("Only JPG, PNG, and WEBP images are allowed.")


def save_upload(data: bytes, uploaded_by: int | None) -> tuple[str, str, int]:
    """Validate `data` as an image and save it under a generated filename.

    Returns (filename, content_type, size). Raises UploadRejected if `data`
    is empty, over MAX_SIZE, or doesn't start with a real JPG/PNG/WEBP
    signature — the claimed upload Content-Type and filename are ignored.
    """
    if not data:
        raise UploadRejected("Choose an image file.")
    if len(data) > MAX_SIZE:
        raise UploadRejected("Images must be 5 MB or smaller.")
    content_type, ext = _sniff(data)
    filename = f"{secrets.token_hex(16)}{ext}"
    settings.MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    (settings.MEDIA_DIR / filename).write_bytes(data)
    return filename, content_type, len(data)
