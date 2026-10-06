"""Turn published Posts into template-ready summaries, grouped by Topic.

Shared by app/publish.py (static export) and app/routes/public.py (live
preview) so the two keep rendering the same grouping, byline, and date for
the same data — same reason they already share app/models.py's queries and
app/services/markdown.render.
"""
from __future__ import annotations

from typing import Callable

from app import models
from app.services import markdown

TOPIC_LABELS = dict(models.TOPIC_CHOICES)

# How many distinct region accent colors app/publish.py's CSS defines
# (.region-0 .. .region-5) — cycles if Staff add a 7th Continent.
REGION_COUNT = 6


def _author_name(post: models.Post) -> str:
    user = models.get_user_by_id(post.author_id) if post.author_id else None
    return user.display_name if user is not None else "CGE Staff"


def _published_date(post: models.Post) -> str:
    stamp = post.published_at or post.created_at or ""
    return stamp[:10]


def _initials(name: str) -> str:
    letters = "".join(part[0] for part in name.split()[:2])
    return letters.upper() or "?"


def post_summary(post: models.Post, href: str) -> dict:
    author_name = _author_name(post)
    return {
        "post": post,
        "href": href,
        "title": post.title,
        "excerpt": markdown.excerpt(post.body),
        "topic_value": post.topic,
        "topic_label": TOPIC_LABELS[post.topic],
        "author_name": author_name,
        "author_initials": _initials(author_name),
        "published_date": _published_date(post),
    }


def region_index(page: models.Page, home: models.Page, continents: list[models.Page]) -> int | None:
    """Which Continent's accent color governs `page` — None for Home itself,
    otherwise the index (mod REGION_COUNT) of the Continent that page lives
    under (or, if `page` is itself a Continent, its own index). Shared by
    every card and page-header band so a Continent's whole subtree (its
    Country and Program pages too) reads in one consistent accent color."""
    if page.id == home.id:
        return None
    root_id = models.nav_root_id(page, home)
    for i, continent in enumerate(continents):
        if continent.id == root_id:
            return i % REGION_COUNT
    return None


def program_stats(program_id: int) -> dict:
    """Published-post count and the distinct Topic labels present, for a
    Program's card on its parent Country's listing."""
    posts = models.list_published_posts_by_program(program_id)
    topics: list[str] = []
    seen: set[str] = set()
    for post in posts:
        if post.topic not in seen:
            seen.add(post.topic)
            topics.append(TOPIC_LABELS[post.topic])
    return {"post_count": len(posts), "topics": topics}


def page_card(
    page: models.Page,
    href: str,
    home: models.Page,
    continents: list[models.Page],
    stats: dict | None = None,
) -> dict:
    """A Continent/Country/Program's card on its parent's listing: title,
    href, a short description teased from the Page's own body, its region
    accent, and — for a Program card — its post count and Topics."""
    return {
        "title": page.title,
        "href": href,
        "excerpt": markdown.excerpt(page.body),
        "region": region_index(page, home, continents),
        "post_count": stats["post_count"] if stats else None,
        "topics": stats["topics"] if stats else None,
    }


def grouped_post_summaries(
    posts: list[models.Post], href_for: Callable[[models.Post], str]
) -> list[tuple[str, str, list[dict]]]:
    """-> [(topic_value, topic_label, [post_summary, ...]), ...], Topics with
    no published Posts omitted."""
    groups = models.group_posts_by_topic(posts)
    return [
        (value, label, [post_summary(post, href_for(post)) for post in group_posts])
        for value, label, group_posts in groups
    ]
