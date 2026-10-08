"""Upload validation, processing, and on-disk storage for Media (#15).

The browser's claimed filename and Content-Type are never trusted: the
actual bytes are sniffed for a real image signature, decoded with Pillow
(itself a second, much stronger validation pass — a truncated or corrupt
file with a valid signature fails here), and the file is saved under a
generated name (never the original filename, a hard constraint).

Every upload is also normalized before it's saved (#15 follow-up):
rotated upright per its EXIF orientation tag, shrunk so its longest side is
at most MAX_DIMENSION (never enlarged), and re-encoded with no metadata at
all — which is what actually strips a phone photo's embedded GPS location,
not just its orientation tag. That's why the size limit could move from
5 MB to 15 MB: every upload is normalized down to a predictable size
regardless of what a phone camera handed over.
"""
from __future__ import annotations

import io
import secrets

from PIL import Image, ImageOps

from app import settings

MAX_SIZE = 15 * 1024 * 1024  # ~15 MB — generous because every upload is
                              # resized down before it's ever written to disk
MAX_DIMENSION = 1600  # longest side, in pixels, after resizing

_SIGNATURES: list[tuple[bytes, str, str]] = [
    (b"\xff\xd8\xff", "image/jpeg", ".jpg"),
    (b"\x89PNG\r\n\x1a\n", "image/png", ".png"),
]
_PIL_FORMAT = {"image/jpeg": "JPEG", "image/png": "PNG", "image/webp": "WEBP"}


class UploadRejected(Exception):
    """Raised for an invalid upload — not a real image, too large, or
    unreadable as the type its signature claims."""


def _sniff(data: bytes) -> tuple[str, str]:
    for signature, content_type, ext in _SIGNATURES:
        if data.startswith(signature):
            return content_type, ext
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp", ".webp"
    raise UploadRejected("Only JPG, PNG, and WEBP images are allowed.")


def _normalize(data: bytes, content_type: str) -> bytes:
    """Upright, at most MAX_DIMENSION on its longest side, no metadata."""
    try:
        image = Image.open(io.BytesIO(data))
        image.load()
    except Exception as exc:
        raise UploadRejected(
            "That file looked like an image but couldn't be read. Try a "
            "different photo."
        ) from exc

    # Bakes a phone's EXIF orientation tag into the actual pixels (so it
    # displays upright everywhere, not just in viewers that honor the tag)
    # and drops that tag from the result.
    image = ImageOps.exif_transpose(image)

    width, height = image.size
    longest = max(width, height)
    if longest > MAX_DIMENSION:
        scale = MAX_DIMENSION / longest
        new_size = (max(round(width * scale), 1), max(round(height * scale), 1))
        image = image.resize(new_size, Image.Resampling.LANCZOS)

    pil_format = _PIL_FORMAT[content_type]
    if pil_format == "JPEG" and image.mode != "RGB":
        image = image.convert("RGB")

    # A fresh image carries no EXIF/ICC/GPS data unless explicitly told to
    # include it — `save()` here never is, so none survives.
    buffer = io.BytesIO()
    save_kwargs = {"quality": 88, "optimize": True} if pil_format == "JPEG" else {}
    image.save(buffer, format=pil_format, **save_kwargs)
    return buffer.getvalue()


def save_upload(data: bytes, uploaded_by: int | None) -> tuple[str, str, int]:
    """Validate `data` as an image, normalize it, and save it under a
    generated filename.

    Returns (filename, content_type, size) for the normalized file — size
    is the stored byte count, not the original upload's. Raises
    UploadRejected if `data` is empty, over MAX_SIZE, doesn't start with a
    real JPG/PNG/WEBP signature, or can't actually be decoded as one — the
    claimed upload Content-Type and filename are ignored throughout.
    """
    if not data:
        raise UploadRejected("Choose an image file.")
    if len(data) > MAX_SIZE:
        raise UploadRejected("Images must be 15 MB or smaller.")
    content_type, ext = _sniff(data)
    normalized = _normalize(data, content_type)
    filename = f"{secrets.token_hex(16)}{ext}"
    settings.MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    (settings.MEDIA_DIR / filename).write_bytes(normalized)
    return filename, content_type, len(normalized)
