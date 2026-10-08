"""A minimal, pure-stdlib PNG encoder for scripts/seed_demo.py's placeholder
cover images (region-colored gradients). Pillow isn't in pyproject.toml, and
CLAUDE.md asks before adding a dependency, so this writes the PNG bytes by
hand instead: an 8-bit RGB image, one unfiltered scanline per row, deflated
with zlib (stdlib), which is exactly what the PNG spec requires IDAT to be.
"""
from __future__ import annotations

import struct
import zlib

RGB = tuple[int, int, int]


def _chunk(tag: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data)) + tag + data
        + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    )


def gradient_png(width: int, height: int, top: RGB, bottom: RGB) -> bytes:
    """A vertical-gradient RGB PNG, `top` at y=0 fading to `bottom`."""
    rows = bytearray()
    for y in range(height):
        t = y / max(height - 1, 1)
        pixel = bytes(
            round(top[c] + (bottom[c] - top[c]) * t) for c in range(3)
        )
        rows.append(0)  # filter type: none
        rows.extend(pixel * width)
    raw = zlib.compress(bytes(rows), 9)
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", header)
        + _chunk(b"IDAT", raw)
        + _chunk(b"IEND", b"")
    )
