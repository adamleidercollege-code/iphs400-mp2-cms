"""Markdown -> sanitized HTML. Pure given its inputs: no FastAPI or SQLite."""
from __future__ import annotations

import re

from markdown_it import MarkdownIt
import nh3

_md = MarkdownIt()
_MD_LIST_BULLET = re.compile(r"(?m)^[ \t]*[-*+][ \t]+")
_MD_MARKERS = re.compile(r"[#>*_`\[\]()!]")
_WHITESPACE = re.compile(r"\s+")


def render(markdown_text: str) -> str:
    """Render Markdown to HTML and strip anything an Ambassador could use to
    inject a script (hard constraint: sanitize before rendering anywhere)."""
    return nh3.clean(_md.render(markdown_text))


def excerpt(markdown_text: str, length: int = 140) -> str:
    """Plain-text teaser for a card: strip common Markdown markers, collapse
    whitespace, and cut at a word boundary. Never marked `| safe` by callers,
    so no sanitization is needed here — Jinja autoescapes it like any text."""
    stripped = _MD_MARKERS.sub(" ", _MD_LIST_BULLET.sub("", markdown_text))
    plain = _WHITESPACE.sub(" ", stripped).strip()
    if len(plain) <= length:
        return plain
    return plain[:length].rsplit(" ", 1)[0] + "…"
