"""Page authoring: the Continent -> Country -> Program tree, admin-only.

Staff-only (require_admin, see app/routes/auth.py): an Ambassador gets a 403,
an anonymous request is redirected to /login, same gate proven on the T01
stub route.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse

from app import models, settings
from app.routes.auth import ensure_csrf_token, require_admin, verify_csrf

templates = Jinja2Templates(directory=str(settings.TEMPLATES))

router = APIRouter(prefix="/admin/pages")


def _get_page_or_404(page_id: int) -> models.Page:
    page = models.get_page_by_id(page_id)
    if page is None:
        raise HTTPException(status_code=404, detail="No such page")
    return page


def _render_form(request, page: models.Page | None, parent_id: int, error: str | None = None):
    parent = _get_page_or_404(parent_id)
    token = ensure_csrf_token(request)
    return templates.TemplateResponse(
        request, "admin/pages_form.html",
        {
            "title": "Edit page" if page else "New page",
            "page": page,
            "parent": parent,
            "csrf_token": token,
            "error": error,
        },
    )


@router.get("")
def list_pages(request: Request, user: models.User = Depends(require_admin)):
    home = models.ensure_home_page()

    def tree(page: models.Page) -> list[dict]:
        return [
            {"page": child, "children": tree(child)}
            for child in models.list_children(page.id)
        ]

    token = ensure_csrf_token(request)
    return templates.TemplateResponse(
        request, "admin/pages_list.html",
        {"title": "Pages", "home": home, "tree": tree(home), "csrf_token": token},
    )


@router.get("/new")
def new_page_form(
    request: Request, parent_id: int, user: models.User = Depends(require_admin)
):
    return _render_form(request, page=None, parent_id=parent_id)


@router.post("/new")
async def create_page(
    request: Request,
    parent_id: int = Form(...),
    title: str = Form(...),
    body: str = Form(""),
    show_in_footer: str | None = Form(None),
    user: models.User = Depends(require_admin),
    _csrf: None = Depends(verify_csrf),
):
    _get_page_or_404(parent_id)
    if not title.strip():
        return _render_form(request, page=None, parent_id=parent_id,
                             error="Title is required.")
    models.create_page(
        parent_id=parent_id, title=title, body=body,
        show_in_footer=bool(show_in_footer), author_id=user.id,
    )
    return RedirectResponse(url="/admin/pages", status_code=303)


@router.get("/{page_id}/edit")
def edit_page_form(
    request: Request, page_id: int, user: models.User = Depends(require_admin)
):
    page = _get_page_or_404(page_id)
    return _render_form(request, page=page, parent_id=page.parent_id)


@router.post("/{page_id}/edit")
async def update_page(
    request: Request,
    page_id: int,
    title: str = Form(...),
    body: str = Form(""),
    show_in_footer: str | None = Form(None),
    user: models.User = Depends(require_admin),
    _csrf: None = Depends(verify_csrf),
):
    page = _get_page_or_404(page_id)
    if not title.strip():
        return _render_form(request, page=page, parent_id=page.parent_id,
                             error="Title is required.")
    models.update_page(page_id, title=title, body=body, show_in_footer=bool(show_in_footer))
    return RedirectResponse(url="/admin/pages", status_code=303)


@router.post("/{page_id}/publish")
async def publish_page(
    page_id: int, user: models.User = Depends(require_admin),
    _csrf: None = Depends(verify_csrf),
):
    _get_page_or_404(page_id)
    models.publish_page(page_id)
    return RedirectResponse(url="/admin/pages", status_code=303)


@router.get("/{page_id}/delete")
def confirm_delete_page(
    request: Request, page_id: int, user: models.User = Depends(require_admin)
):
    page = _get_page_or_404(page_id)
    if page.parent_id is None:
        raise HTTPException(status_code=400, detail="Cannot delete the Home page")
    token = ensure_csrf_token(request)
    return templates.TemplateResponse(
        request, "admin/pages_delete.html",
        {"title": "Delete page?", "page": page, "csrf_token": token},
    )


@router.post("/{page_id}/delete")
async def delete_page(
    page_id: int, user: models.User = Depends(require_admin),
    _csrf: None = Depends(verify_csrf),
):
    try:
        models.delete_page(page_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return RedirectResponse(url="/admin/pages", status_code=303)
