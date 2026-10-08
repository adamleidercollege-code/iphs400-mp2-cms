"""Page authoring: the Continent -> Country -> Program tree, admin-only.

Staff-only (require_admin, see app/routes/auth.py): an Ambassador gets a 403,
an anonymous request is redirected to /login, same gate proven on the T01
stub route.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.templating import Jinja2Templates

from app import models, settings
from app.routes.auth import require_admin, verify_csrf
from app.services import console_shell, markdown, media_store, post_view

templates = Jinja2Templates(directory=str(settings.TEMPLATES))

router = APIRouter(prefix="/admin/pages")


def _get_page_or_404(page_id: int) -> models.Page:
    page = models.get_page_by_id(page_id)
    if page is None:
        raise HTTPException(status_code=404, detail="No such page")
    return page


def _render_form(
    request, user: models.User, page: models.Page | None, parent_id: int,
    error: str | None = None,
):
    parent = _get_page_or_404(parent_id)
    is_program = page is not None and models.is_program_page(page)
    cover = (
        post_view.media_cover(page.cover_media_id, post_view.media_href_for("/"))
        if page else None
    )
    context = console_shell.console_context(request, user)
    context.update({
        "title": "Edit page" if page else "New page",
        "page": page,
        "parent": parent,
        "error": error,
        "is_program": is_program,
        "cover": cover,
        "just_added": _just_added_media(request),
        "formatting_help": markdown.formatting_help_examples(),
        # A Page has no live Preview pane and no inline "Add image" upload
        # (only a Program's cover, above) — the shared formatting-help
        # partial drops the tips that mention either.
        "show_preview_tip": False,
        "show_image_tip": False,
    })
    return templates.TemplateResponse(request, "admin/pages_form.html", context)


def _just_added_media(request: Request) -> dict | None:
    """The Media a redirect back from a successful cover upload just added
    (console_shell.redirect_with_flash's `added_media_id`) — {href, alt}
    for the small thumbnail next to the upload confirmation."""
    added_media_id = request.query_params.get("added_media_id")
    if not added_media_id or not added_media_id.isdigit():
        return None
    media = models.get_media_by_id(int(added_media_id))
    if media is None:
        return None
    return {"href": f"/media/{media.filename}", "alt": media.alt_text}


@router.get("")
def list_pages(request: Request, user: models.User = Depends(require_admin)):
    home = models.ensure_home_page()

    def tree(page: models.Page) -> list[dict]:
        return [
            {"page": child, "children": tree(child)}
            for child in models.list_children(page.id)
        ]

    context = console_shell.console_context(request, user)
    context.update({"title": "Pages", "home": home, "tree": tree(home)})
    return templates.TemplateResponse(request, "admin/pages_list.html", context)


@router.get("/new")
def new_page_form(
    request: Request, parent_id: int, user: models.User = Depends(require_admin)
):
    return _render_form(request, user, page=None, parent_id=parent_id)


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
        return _render_form(request, user, page=None, parent_id=parent_id,
                             error="Title is required.")
    models.create_page(
        parent_id=parent_id, title=title, body=body,
        show_in_footer=bool(show_in_footer), author_id=user.id,
    )
    return console_shell.redirect_with_flash("/admin/pages", "Page created.")


@router.get("/{page_id}/edit")
def edit_page_form(
    request: Request, page_id: int, user: models.User = Depends(require_admin)
):
    page = _get_page_or_404(page_id)
    return _render_form(request, user, page=page, parent_id=page.parent_id)


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
        return _render_form(request, user, page=page, parent_id=page.parent_id,
                             error="Title is required.")
    models.update_page(page_id, title=title, body=body, show_in_footer=bool(show_in_footer))
    return console_shell.redirect_with_flash("/admin/pages", "Page saved.")


@router.post("/{page_id}/publish")
async def publish_page(
    page_id: int, user: models.User = Depends(require_admin),
    _csrf: None = Depends(verify_csrf),
):
    _get_page_or_404(page_id)
    models.publish_page(page_id)
    return console_shell.redirect_with_flash("/admin/pages", "Page published.")


@router.get("/{page_id}/delete")
def confirm_delete_page(
    request: Request, page_id: int, user: models.User = Depends(require_admin)
):
    page = _get_page_or_404(page_id)
    if page.parent_id is None:
        raise HTTPException(status_code=400, detail="Cannot delete the Home page")
    context = console_shell.console_context(request, user)
    context.update({"title": "Delete page?", "page": page})
    return templates.TemplateResponse(request, "admin/pages_delete.html", context)


@router.post("/{page_id}/delete")
async def delete_page(
    page_id: int, user: models.User = Depends(require_admin),
    _csrf: None = Depends(verify_csrf),
):
    try:
        models.delete_page(page_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return console_shell.redirect_with_flash("/admin/pages", "Page deleted.")


@router.post("/{page_id}/cover")
async def set_page_cover(
    request: Request,
    page_id: int,
    image: UploadFile = File(...),
    alt_text: str = Form(""),
    user: models.User = Depends(require_admin),
    _csrf: None = Depends(verify_csrf),
):
    page = _get_page_or_404(page_id)
    if not models.is_program_page(page):
        raise HTTPException(status_code=400, detail="Only a Program page has a cover image")
    alt_text = alt_text.strip()
    if not alt_text:
        return _render_form(request, user, page=page, parent_id=page.parent_id,
                             error="Alt text is required for the cover image.")
    data = await image.read()
    try:
        filename, content_type, size = media_store.save_upload(data, user.id)
    except media_store.UploadRejected as exc:
        return _render_form(request, user, page=page, parent_id=page.parent_id,
                             error=str(exc))
    media = models.create_media(filename=filename, content_type=content_type,
                                 size=size, alt_text=alt_text, uploaded_by=user.id)
    models.set_page_cover(page.id, media.id)
    return console_shell.redirect_with_flash(
        f"/admin/pages/{page.id}/edit", "Cover image set.",
        fragment="cover-section", added_media_id=str(media.id))
