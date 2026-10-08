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


# The UI-facing name for each role, per CONTEXT.md's Role entry: admin shows
# as Staff, editor as Ambassador.
ROLE_LABELS = {"admin": "Staff", "editor": "Ambassador"}

_MONTHS = ["January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December"]


def _author(post: models.Post) -> tuple[str, str]:
    """-> (display name, UI role label) for a Post's byline."""
    user = models.get_user_by_id(post.author_id) if post.author_id else None
    if user is None:
        return "CGE Staff", ROLE_LABELS["admin"]
    return user.display_name, ROLE_LABELS.get(user.role, ROLE_LABELS["editor"])


def _published_date(post: models.Post) -> str:
    """ISO stamp -> "6 October 2026". Falls back to the raw date if the stamp
    isn't the shape SQLite writes."""
    stamp = (post.published_at or post.created_at or "")[:10]
    try:
        year, month, day = (int(part) for part in stamp.split("-"))
        return f"{day} {_MONTHS[month - 1]} {year}"
    except (ValueError, IndexError):
        return stamp


def _initials(name: str) -> str:
    letters = "".join(part[0] for part in name.split()[:2])
    return letters.upper() or "?"


def media_href_for(prefix: str) -> Callable[[int], str]:
    """A resolver for a Media id -> its href from wherever `prefix` is the
    site-root-relative path (e.g. "../../" for a nested static page, "/"
    for the live preview — same idea as app.publish's per-page site_root)."""

    def _href(media_id: int) -> str:
        media = models.get_media_by_id(media_id)
        return f"{prefix}media/{media.filename}" if media else "#"

    return _href


def owned_media_ids(post: models.Post, text: str | None = None) -> set[int]:
    """Every `media/<id>` reference in `text` (post.body if not given) that
    this Post actually uploaded (app.routes.posts.add_post_image sets
    Media.post_id at upload time) — hand-typing another id (someone else's
    upload, a draft's media, a Program's cover) into the body text must
    never pull that file into this Post's render or into app.publish's copy
    step. Ownership is checked against the Post's own id, not the text's
    source, so the admin preview's just-submitted (not yet saved) body is
    covered too."""
    owned = set()
    for media_id in markdown.referenced_media_ids(post.body if text is None else text):
        media = models.get_media_by_id(media_id)
        if media is not None and media.post_id == post.id:
            owned.add(media_id)
    return owned


def post_body_media_href_for(
    post: models.Post, prefix: str, text: str | None = None
) -> Callable[[int], str]:
    """A `media_href` resolver for app.services.markdown.render(...),
    scoped to only the `media/<id>` ids this Post owns (owned_media_ids
    above) — anything else resolves to "#" rather than ever rendering (or
    letting app.publish copy) a file this Post was never granted."""
    owned = owned_media_ids(post, text)

    def _href(media_id: int) -> str:
        if media_id not in owned:
            return "#"
        media = models.get_media_by_id(media_id)
        return f"{prefix}media/{media.filename}" if media else "#"

    return _href


def media_cover(
    media_id: int | None, media_href: Callable[[int], str] | None
) -> dict | None:
    """-> {"href", "alt"} for a Page's or Post's cover_media_id, resolved
    with `media_href` — None if there is no cover (or no resolver)."""
    if not media_id or media_href is None:
        return None
    media = models.get_media_by_id(media_id)
    if media is None:
        return None
    return {"href": media_href(media_id), "alt": media.alt_text}


def post_summary(
    post: models.Post, href: str, media_href: Callable[[int], str] | None = None
) -> dict:
    author_name, author_role = _author(post)
    return {
        "post": post,
        "href": href,
        "title": post.title,
        "excerpt": markdown.excerpt(post.body),
        "topic_value": post.topic,
        "topic_label": TOPIC_LABELS[post.topic],
        "tags": models.get_tags_for_post(post.id),
        "cover": media_cover(post.cover_media_id, media_href),
        "author_name": author_name,
        "author_role": author_role,
        "author_initials": _initials(author_name),
        "published_date": _published_date(post),
    }


def distinct_tags(post_groups: list[tuple[str, str, list[dict]]]) -> list[models.Tag]:
    """Every Tag actually used by a Program's currently-shown Posts, in name
    order — the options for its reader-facing Tag filter. A Tag nobody on
    this Program has used yet is left out, same as `group_posts_by_topic`
    omits an empty Topic."""
    seen: dict[int, models.Tag] = {}
    for _value, _label, summaries in post_groups:
        for summary in summaries:
            for tag in summary["tags"]:
                seen[tag.id] = tag
    return sorted(seen.values(), key=lambda t: t.name)


def children_heading(page: models.Page, home: models.Page) -> str:
    """What to call a Page's list of child Pages, in the reader's words
    rather than the tree's: Home browses regions, a Continent lists its
    Countries, a Country lists its Programs."""
    if page.id == home.id:
        return "Explore by region"
    if models.is_continent_page(page):
        return f"Countries in {page.title}"
    if models.is_country_page(page):
        return f"Programs in {page.title}"
    return "Pages"


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
    media_href: Callable[[int], str] | None = None,
) -> dict:
    """A Continent/Country/Program's card on its parent's listing: title,
    href, a short description teased from the Page's own body, its region
    accent, cover image (a Program's own, if Staff set one), and — for a
    Program card — its post count and Topics."""
    return {
        "title": page.title,
        "href": href,
        "excerpt": markdown.excerpt(page.body),
        "region": region_index(page, home, continents),
        "cover": media_cover(page.cover_media_id, media_href),
        "post_count": stats["post_count"] if stats else None,
        "topics": stats["topics"] if stats else None,
    }


def grouped_post_summaries(
    posts: list[models.Post],
    href_for: Callable[[models.Post], str],
    media_href: Callable[[int], str] | None = None,
) -> list[tuple[str, str, list[dict]]]:
    """-> [(topic_value, topic_label, [post_summary, ...]), ...], Topics with
    no published Posts omitted."""
    groups = models.group_posts_by_topic(posts)
    return [
        (
            value,
            label,
            [post_summary(post, href_for(post), media_href) for post in group_posts],
        )
        for value, label, group_posts in groups
    ]
