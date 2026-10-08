"""The public site, served live from the database.

This is the admin console's "preview" the Pages ticket asks for: Staff see a
published change here immediately, before anyone runs `cms publish`. It and
the static exporter (app/publish.py) share the same page-tree queries in
app/models.py and the same Markdown renderer, so the two stay in sync.

Only PUBLISHED pages are reachable here — same rule as the static export.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates

from app import models, settings
from app.publish import CSS
from app.services import markdown, post_view, search_index

templates = Jinja2Templates(directory=str(settings.TEMPLATES))

router = APIRouter()


def resolve(path: str) -> tuple[str, models.Page] | tuple[str, models.Post, models.Page] | None:
    """A Page by its full path, or — one segment further, under a Program —
    a published Post by slug. Returns None on no match."""
    home = models.ensure_home_page()
    segments = [s for s in path.strip("/").split("/") if s]
    current = home
    for i, segment in enumerate(segments):
        child = models.get_child_by_slug(current.id, segment)
        if child is not None:
            current = child
            continue
        if i == len(segments) - 1 and models.is_program_page(current):
            post = models.get_published_post_by_slug(current.id, segment)
            if post is not None:
                return "post", post, current
        return None
    return "page", current


def _path_for(page: models.Page, home: models.Page) -> str:
    if page.id == home.id:
        return "/"
    chain = [p.slug for p in models.list_ancestors(page) if p.id != home.id]
    chain.append(page.slug)
    return "/" + "/".join(chain) + "/"


def page_context(page: models.Page) -> dict:
    home = models.ensure_home_page()
    continents = models.list_published_children(home.id)
    footer_pages = models.list_footer_pages()
    ancestors = [a for a in models.list_ancestors(page) if a.id != page.id]
    children = models.list_published_children(page.id)
    active_id = models.nav_root_id(page, home)
    is_country = models.is_country_page(page)
    is_program = models.is_program_page(page)
    chain = [a.slug for a in models.list_ancestors(page) if a.id != home.id] + (
        [page.slug] if page.id != home.id else []
    )
    search_scope_chain = (
        chain if (models.is_continent_page(page) or is_country or is_program) else None
    )

    # Live preview is always served from the server root, so every Media
    # href is root-relative regardless of how deep `page` sits (unlike
    # app.publish's static export, which recomputes a relative prefix per
    # page depth).
    media_href = post_view.media_href_for("/")

    post_groups = None
    tag_filters = None
    if is_program:
        page_href = _path_for(page, home)
        posts = models.list_published_posts_by_program(page.id)
        post_groups = post_view.grouped_post_summaries(
            posts, lambda post: page_href.rstrip("/") + f"/{post.slug}/",
            media_href=media_href,
        )
        tag_filters = post_view.distinct_tags(post_groups)

    intro_md, rest_md = markdown.split_intro(page.body)
    sections = []
    if models.is_standalone_page(page):
        sections = [
            {"heading": heading, "body_html": markdown.render(body)}
            for heading, body in markdown.split_sections(rest_md)
        ]
        rest_md = markdown.strip_sections(rest_md)

    return {
        "page": page,
        "intro_html": markdown.render(intro_md),
        "body_html": markdown.render(rest_md),
        "sections": sections,
        "region": post_view.region_index(page, home, continents),
        "nav": [{"title": home.title, "href": "/", "active": active_id == home.id}] + [
            {"title": c.title, "href": _path_for(c, home), "active": active_id == c.id}
            for c in continents
        ],
        "breadcrumb": [{"title": a.title, "href": _path_for(a, home)} for a in ancestors],
        "footer_links": [
            {"title": f.title, "href": _path_for(f, home)} for f in footer_pages
        ],
        "children": [
            post_view.page_card(
                c, _path_for(c, home), home, continents,
                stats=post_view.program_stats(c.id) if is_country else None,
                media_href=media_href,
            )
            for c in children
        ],
        "children_heading": post_view.children_heading(page, home),
        "post_groups": post_groups,
        "tag_filters": tag_filters,
        "site_root": "",
        "search_index_href": "/search-index.json",
        "search_scope_chain": search_scope_chain,
    }


def post_context(post: models.Post, program: models.Page) -> dict:
    home = models.ensure_home_page()
    continents = models.list_published_children(home.id)
    footer_pages = models.list_footer_pages()
    ancestors = [a for a in models.list_ancestors(program) if a.id != program.id]
    program_href = _path_for(program, home)
    post_href = program_href.rstrip("/") + f"/{post.slug}/"
    media_href = post_view.media_href_for("/")
    summary = post_view.post_summary(post, post_href, media_href=media_href)
    active_id = models.nav_root_id(program, home)
    more_from = [
        post_view.post_summary(
            other, program_href.rstrip("/") + f"/{other.slug}/", media_href=media_href,
        )
        for other in models.list_published_posts_by_program(program.id)
        if other.id != post.id
    ][:2]

    return {
        "post": post,
        "body_html": markdown.render(post.body, media_href=media_href),
        "topic_label": summary["topic_label"],
        "tags": summary["tags"],
        "cover": summary["cover"],
        "author_name": summary["author_name"],
        "author_role": summary["author_role"],
        "author_initials": summary["author_initials"],
        "published_date": summary["published_date"],
        "region": post_view.region_index(program, home, continents),
        "more_from": more_from,
        "program_href": program_href,
        "program_title": program.title,
        "nav": [{"title": home.title, "href": "/", "active": active_id == home.id}] + [
            {"title": c.title, "href": _path_for(c, home), "active": active_id == c.id}
            for c in continents
        ],
        "breadcrumb": [{"title": a.title, "href": _path_for(a, home)} for a in ancestors]
        + [{"title": program.title, "href": program_href}],
        "footer_links": [
            {"title": f.title, "href": _path_for(f, home)} for f in footer_pages
        ],
        "site_root": "",
        "search_index_href": "/search-index.json",
    }


@router.get("/search-index.json")
def search_index_json():
    """Live-preview counterpart to the search-index.json app.publish writes
    into site/ — same shape, built from the live database instead of a
    static export, so the admin console's preview can exercise search before
    anyone runs `cms publish`."""
    entries = search_index.build_index(lambda chain: "/" + "/".join(chain) + "/")
    return JSONResponse(entries)


@router.get("/{path:path}")
def public_page(request: Request, path: str):
    resolved = resolve(path)
    if resolved is None:
        raise HTTPException(status_code=404)

    if resolved[0] == "post":
        _kind, post, program = resolved
        return templates.TemplateResponse(
            request, "public/post.html",
            {"title": post.title, "inline_css": CSS, **post_context(post, program)},
        )

    _kind, page = resolved
    if page.status != "published":
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(
        request, "public/page.html",
        {"title": page.title, "inline_css": CSS, **page_context(page)},
    )
