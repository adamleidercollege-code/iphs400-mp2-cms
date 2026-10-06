"""Markdown -> sanitized HTML. Pure given its inputs: no FastAPI or SQLite."""
from __future__ import annotations

import re

from markdown_it import MarkdownIt
import nh3

_md = MarkdownIt()
_MD_LIST_BULLET = re.compile(r"(?m)^[ \t]*[-*+][ \t]+")
# Styling markers that always sit directly against a word (**bold**, `code`,
# # heading, > quote) — safe to delete outright. Deleting rather than
# spacing these out avoids a stray space before trailing punctuation, e.g.
# "**Africa**." must become "Africa.", not "Africa ."
_MD_STYLE_MARKERS = re.compile(r"[#>*_`]")
# Link/image punctuation ([text](url), ![alt](url)) separates two tokens
# that aren't otherwise space-separated, so these are replaced with a space
# instead of deleted, to avoid gluing "text" and "url" together.
_MD_LINK_PUNCT = re.compile(r"[!\[\]()]")
_WHITESPACE = re.compile(r"\s+")
# Catches any stray space left before trailing punctuation by the
# substitutions above, however it got there — e.g. "[text](url)." stripping
# to "text url ." without this, since the "." follows a deleted ")".
_SPACE_BEFORE_PUNCT = re.compile(r"\s+([.,;:!?])")


def render(markdown_text: str) -> str:
    """Render Markdown to HTML and strip anything an Ambassador could use to
    inject a script (hard constraint: sanitize before rendering anywhere)."""
    return nh3.clean(_md.render(markdown_text))


def excerpt(markdown_text: str, length: int = 140) -> str:
    """Plain-text teaser for a card: strip common Markdown markers, collapse
    whitespace, and cut at a word boundary. Never marked `| safe` by callers,
    so no sanitization is needed here — Jinja autoescapes it like any text."""
    no_bullets = _MD_LIST_BULLET.sub("", markdown_text)
    no_style = _MD_STYLE_MARKERS.sub("", no_bullets)
    no_link_punct = _MD_LINK_PUNCT.sub(" ", no_style)
    collapsed = _WHITESPACE.sub(" ", no_link_punct).strip()
    plain = _SPACE_BEFORE_PUNCT.sub(r"\1", collapsed)
    if len(plain) <= length:
        return plain
    return plain[:length].rsplit(" ", 1)[0] + "…"
