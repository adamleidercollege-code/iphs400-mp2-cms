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

# Flag emoji for the T11 country-card treatment. Countries Staff add later
# that aren't listed here just render without a flag (optional per spec).
COUNTRY_FLAGS = {
    "Japan": "🇯🇵", "South Korea": "🇰🇷", "Kenya": "🇰🇪", "South Africa": "🇿🇦",
    "Spain": "🇪🇸", "France": "🇫🇷", "Italy": "🇮🇹", "Germany": "🇩🇪",
    "United Kingdom": "🇬🇧", "China": "🇨🇳", "India": "🇮🇳", "Brazil": "🇧🇷",
    "Mexico": "🇲🇽", "Australia": "🇦🇺", "Egypt": "🇪🇬", "Morocco": "🇲🇦",
    "Ghana": "🇬🇭", "Tanzania": "🇹🇿", "Thailand": "🇹🇭", "Vietnam": "🇻🇳",
    "Argentina": "🇦🇷", "Chile": "🇨🇱", "Peru": "🇵🇪", "Portugal": "🇵🇹",
    "Netherlands": "🇳🇱", "Ireland": "🇮🇪", "Greece": "🇬🇷", "Turkey": "🇹🇷",
    "New Zealand": "🇳🇿", "Indonesia": "🇮🇩", "Jordan": "🇯🇴", "Senegal": "🇸🇳",
}


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


def page_card(page: models.Page, href: str, show_flag: bool) -> dict:
    """A Continent/Country/Program's card on its parent's listing: title,
    href, and a short description teased from the Page's own body."""
    return {
        "title": page.title,
        "href": href,
        "excerpt": markdown.excerpt(page.body),
        "flag": COUNTRY_FLAGS.get(page.title, "") if show_flag else "",
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
