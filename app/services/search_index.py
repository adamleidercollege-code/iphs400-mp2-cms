"""Build the client-side search index (#10): one entry per published Post —
title, body text, and tags — scoped to its owning Program's slug chain so a
Continent/Country/Program page's search box can filter to its own subtree.

Shared by app/publish.py (writes it as a static search-index.json) and
app/routes/public.py (serves the same shape live, for the admin preview).
Search itself runs entirely in the browser against whichever of those two
this module produced — this module only ever reads, never serves a query.
"""
from __future__ import annotations

from typing import Callable

from app import models
from app.services import markdown


def build_index(href_for: Callable[[list[str]], str]) -> list[dict]:
    """`href_for` turns a Post's full slug chain (ancestors + Program + Post)
    into the link a search result should point at — the one thing that
    differs between a static export (relative, .../index.html) and the live
    preview (root-absolute, matching app.routes.public's own route shape)."""
    home = models.ensure_home_page()
    entries: list[dict] = []
    for page in models.list_all_pages():
        if page.status != "published" or not models.is_program_page(page):
            continue
        chain = [a.slug for a in models.list_ancestors(page) if a.id != home.id] + [page.slug]
        for post in models.list_published_posts_by_program(page.id):
            entries.append({
                "title": post.title,
                "text": markdown.plain_text(post.body),
                "tags": [tag.name for tag in models.get_tags_for_post(post.id)],
                "chain": chain,
                "href": href_for(chain + [post.slug]),
            })
    return entries
