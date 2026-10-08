"""Serves an uploaded Media file for the live admin preview (#15).

Filenames are always `secrets.token_hex(...)` plus a known extension
(app.services.media_store), never a path a request could walk, but the
basename check below is defensive against a crafted request anyway. The
static export (app/publish.py) copies the same files into site/media/
instead of serving them from here.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app import settings

router = APIRouter()


@router.get("/media/{filename}")
def media_file(filename: str):
    if filename != Path(filename).name:
        raise HTTPException(status_code=404)
    path = settings.MEDIA_DIR / filename
    if not path.is_file():
        raise HTTPException(status_code=404)
    return FileResponse(path)
