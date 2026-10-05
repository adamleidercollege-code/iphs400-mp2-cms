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
from app.services import markdown

templates = Jinja2Templates(directory=str(settings.TEMPLATES))

router = APIRouter()


def resolve_page(path: str) -> models.Page | None:
    home = models.ensure_home_page()
    segments = [s for s in path.strip("/").split("/") if s]
    current = home
    for segment in segments:
        child = models.get_child_by_slug(current.id, segment)
        if child is None:
            return None
        current = child
    return current


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
    return {
        "page": page,
        "body_html": markdown.render(page.body),
        "nav": [{"title": home.title, "href": "/"}] + [
            {"title": c.title, "href": _path_for(c, home)} for c in continents
        ],
        "breadcrumb": [{"title": a.title, "href": _path_for(a, home)} for a in ancestors]
        + [{"title": page.title, "href": _path_for(page, home)}],
        "footer_links": [
            {"title": f.title, "href": _path_for(f, home)} for f in footer_pages
        ],
        "children": [
            {"title": c.title, "href": _path_for(c, home)} for c in children
        ],
    }


@router.get("/{path:path}")
def public_page(request: Request, path: str):
    page = resolve_page(path)
    if page is None or page.status != "published":
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(
        request, "public/page.html",
        {"title": page.title, "inline_css": CSS, **page_context(page)},
    )
