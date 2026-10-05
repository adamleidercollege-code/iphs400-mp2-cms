"""Markdown -> sanitized HTML. Pure given its inputs: no FastAPI or SQLite."""
from __future__ import annotations

from markdown_it import MarkdownIt
import nh3

_md = MarkdownIt()


def render(markdown_text: str) -> str:
    """Render Markdown to HTML and strip anything an Ambassador could use to
    inject a script (hard constraint: sanitize before rendering anywhere)."""
    return nh3.clean(_md.render(markdown_text))
