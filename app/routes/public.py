"""The public site, served live from the database.

This is the admin console's "preview" the Pages ticket asks for: Staff see a
published change here immediately, before anyone runs `cms publish`. It and
the static exporter (app/publish.py) share the same page-tree queries in
app/models.py and the same Markdown renderer, so the two stay in sync.

Only PUBLISHED pages are reachable here — same rule as the static export.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.templating import Jinja2Templates

from app import models, settings
from app.publish import CSS
from app.services import markdown, post_view

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
    show_flag = models.is_continent_page(page)

    post_groups = None
    if models.is_program_page(page):
        page_href = _path_for(page, home)
        posts = models.list_published_posts_by_program(page.id)
        post_groups = post_view.grouped_post_summaries(
            posts, lambda post: page_href.rstrip("/") + f"/{post.slug}/"
        )

    return {
        "page": page,
        "body_html": markdown.render(page.body),
        "nav": [{"title": home.title, "href": "/", "active": active_id == home.id}] + [
            {"title": c.title, "href": _path_for(c, home), "active": active_id == c.id}
            for c in continents
        ],
        "breadcrumb": [{"title": a.title, "href": _path_for(a, home)} for a in ancestors]
        + [{"title": page.title, "href": _path_for(page, home)}],
        "footer_links": [
            {"title": f.title, "href": _path_for(f, home)} for f in footer_pages
        ],
        "children": [
            post_view.page_card(c, _path_for(c, home), show_flag) for c in children
        ],
        "post_groups": post_groups,
    }


def post_context(post: models.Post, program: models.Page) -> dict:
    home = models.ensure_home_page()
    continents = models.list_published_children(home.id)
    footer_pages = models.list_footer_pages()
    ancestors = [a for a in models.list_ancestors(program) if a.id != program.id]
    program_href = _path_for(program, home)
    post_href = program_href.rstrip("/") + f"/{post.slug}/"
    summary = post_view.post_summary(post, post_href)
    active_id = models.nav_root_id(program, home)

    return {
        "post": post,
        "body_html": markdown.render(post.body),
        "topic_label": summary["topic_label"],
        "author_name": summary["author_name"],
        "published_date": summary["published_date"],
        "program_href": program_href,
        "program_title": program.title,
        "nav": [{"title": home.title, "href": "/", "active": active_id == home.id}] + [
            {"title": c.title, "href": _path_for(c, home), "active": active_id == c.id}
            for c in continents
        ],
        "breadcrumb": [{"title": a.title, "href": _path_for(a, home)} for a in ancestors]
        + [{"title": program.title, "href": program_href},
           {"title": post.title, "href": post_href}],
        "footer_links": [
            {"title": f.title, "href": _path_for(f, home)} for f in footer_pages
        ],
    }


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
