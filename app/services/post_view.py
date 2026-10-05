"""Turn published Posts into template-ready summaries, grouped by Topic.

Shared by app/publish.py (static export) and app/routes/public.py (live
preview) so the two keep rendering the same grouping, byline, and date for
the same data — same reason they already share app/models.py's queries and
app/services/markdown.render.
"""
from __future__ import annotations

from typing import Callable

from app import models

TOPIC_LABELS = dict(models.TOPIC_CHOICES)


def _author_name(post: models.Post) -> str:
    user = models.get_user_by_id(post.author_id) if post.author_id else None
    return user.display_name if user is not None else "CGE Staff"


def _published_date(post: models.Post) -> str:
    stamp = post.published_at or post.created_at or ""
    return stamp[:10]


def post_summary(post: models.Post, href: str) -> dict:
    return {
        "post": post,
        "href": href,
        "title": post.title,
        "topic_label": TOPIC_LABELS[post.topic],
        "author_name": _author_name(post),
        "published_date": _published_date(post),
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
