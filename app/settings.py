"""Configuration, read from the environment (never hard-code secrets)."""
from __future__ import annotations

import os
from pathlib import Path

from app.env_file import load_into_environ

ROOT = Path(__file__).resolve().parents[1]
load_into_environ(ROOT / ".env")  # a real exported env var still always wins

TEMPLATES = ROOT / "templates"
SITE = ROOT / "site"
MEDIA_DIR = Path(os.environ.get("CMS_MEDIA_DIR", ROOT / "uploads"))

SECRET_KEY = os.environ.get("CMS_SECRET_KEY", "dev-only-not-for-production")
DATABASE_PATH = Path(os.environ.get("CMS_DATABASE", ROOT / "cms.db"))
SITE_TITLE = os.environ.get("CMS_SITE_TITLE", "My CMS")
# Set this to your Pages URL once you deploy, e.g.
# https://yourname.github.io/iphs400-mp2-cms/
BASE_PATH = os.environ.get("CMS_BASE_PATH", "")
