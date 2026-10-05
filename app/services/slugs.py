"""Slug generation — pure, no FastAPI or SQLite dependency."""
from __future__ import annotations

import re

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def slugify(title: str) -> str:
    slug = _NON_ALNUM.sub("-", title.strip().lower()).strip("-")
    return slug or "page"


def dedupe(slug: str, sibling_slugs: set[str]) -> str:
    """Append -2, -3, ... until `slug` doesn't collide with a sibling's."""
    if slug not in sibling_slugs:
        return slug
    n = 2
    while f"{slug}-{n}" in sibling_slugs:
        n += 1
    return f"{slug}-{n}"
