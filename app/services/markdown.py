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
# A "## Heading" line, which splits a Page's body into the intro that heads
# the page and the sections rendered below it as cards.
_H2_SPLIT = re.compile(r"(?m)^##[ \t]+(.+?)[ \t]*$")


def render(markdown_text: str) -> str:
    """Render Markdown to HTML and strip anything an Ambassador could use to
    inject a script (hard constraint: sanitize before rendering anywhere)."""
    return nh3.clean(_md.render(markdown_text))


def plain_text(markdown_text: str) -> str:
    """Full Markdown -> plain text, stripped of its own marker syntax. Shared
    by `excerpt` (which then truncates) and the search index (#10), which
    needs the whole body to match against, not a card teaser. Never marked
    `| safe` by callers, so no sanitization is needed here — Jinja autoescapes
    it like any text, and the search index is plain JSON, not markup."""
    no_bullets = _MD_LIST_BULLET.sub("", markdown_text)
    no_style = _MD_STYLE_MARKERS.sub("", no_bullets)
    no_link_punct = _MD_LINK_PUNCT.sub(" ", no_style)
    collapsed = _WHITESPACE.sub(" ", no_link_punct).strip()
    return _SPACE_BEFORE_PUNCT.sub(r"\1", collapsed)


def excerpt(markdown_text: str, length: int = 140) -> str:
    """Plain-text teaser for a card: `plain_text`, cut at a word boundary."""
    plain = plain_text(markdown_text)
    if len(plain) <= length:
        return plain
    return plain[:length].rsplit(" ", 1)[0] + "…"


def split_intro(markdown_text: str) -> tuple[str, str]:
    """-> (first paragraph, everything after it). The first paragraph heads
    the page (inside the tinted band); the rest renders in a panel below, so
    a long body never turns the band into the whole page."""
    stripped = markdown_text.strip()
    if not stripped:
        return "", ""
    head, separator, tail = stripped.partition("\n\n")
    if head.lstrip().startswith("##"):  # a body that opens with a section
        return "", stripped
    return head.strip(), tail.strip() if separator else ""


def split_sections(markdown_text: str) -> list[tuple[str, str]]:
    """-> [(heading, body markdown), ...] for each "## Heading" in the text.
    A standalone Page renders these as cards, so Staff get a structured
    layout by writing ordinary Markdown sections — no template change."""
    matches = list(_H2_SPLIT.finditer(markdown_text))
    sections = []
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(markdown_text)
        sections.append((match.group(1).strip(), markdown_text[match.end():end].strip()))
    return sections


def strip_sections(markdown_text: str) -> str:
    """The text before the first "## Heading" — the part split_sections leaves
    behind."""
    match = _H2_SPLIT.search(markdown_text)
    return markdown_text[: match.start()].strip() if match else markdown_text.strip()
