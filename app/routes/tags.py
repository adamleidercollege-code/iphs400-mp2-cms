"""Tag management (#14): a Staff-curated, multi-select label set, distinct
from Topic (CONTEXT.md). Admin-only (require_admin, same gate as Pages and
Accounts): only Staff create, rename, or delete a Tag here. An Ambassador
still picks from the existing list when writing a Post (app/routes/posts.py)
but never reaches a route in this module.
"""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.templating import Jinja2Templates

from app import models, settings
from app.routes.auth import require_admin, verify_csrf
from app.services import console_shell

templates = Jinja2Templates(directory=str(settings.TEMPLATES))

router = APIRouter(prefix="/admin/tags")

DUPLICATE_NAME_ERROR = "A tag with that name already exists."


def _get_tag_or_404(tag_id: int) -> models.Tag:
    tag = models.get_tag_by_id(tag_id)
    if tag is None:
        raise HTTPException(status_code=404, detail="No such tag")
    return tag


def _render_form(
    request: Request, user: models.User, tag: models.Tag | None,
    error: str | None = None, name: str = "", status_code: int = 200,
):
    context = console_shell.console_context(request, user)
    context.update({
        "title": "Rename tag" if tag else "New tag",
        "tag": tag,
        "error": error,
        "form_name": name,
    })
    return templates.TemplateResponse(
        request, "admin/tags_form.html", context, status_code=status_code,
    )


@router.get("")
def list_tags(request: Request, user: models.User = Depends(require_admin)):
    context = console_shell.console_context(request, user)
    context.update({"title": "Tags", "tags": models.list_tags()})
    return templates.TemplateResponse(request, "admin/tags_list.html", context)


@router.get("/new")
def new_tag_form(request: Request, user: models.User = Depends(require_admin)):
    return _render_form(request, user, tag=None)


@router.post("/new")
async def create_tag(
    request: Request,
    name: str = Form(""),
    user: models.User = Depends(require_admin),
    _csrf: None = Depends(verify_csrf),
):
    name = name.strip()
    if not name:
        return _render_form(request, user, tag=None, error="Name is required.",
                             name=name, status_code=400)
    try:
        models.create_tag(name)
    except sqlite3.IntegrityError:
        return _render_form(request, user, tag=None, error=DUPLICATE_NAME_ERROR,
                             name=name, status_code=400)
    return console_shell.redirect_with_flash("/admin/tags", "Tag created.")


@router.get("/{tag_id}/edit")
def edit_tag_form(
    request: Request, tag_id: int, user: models.User = Depends(require_admin)
):
    tag = _get_tag_or_404(tag_id)
    return _render_form(request, user, tag=tag, name=tag.name)


@router.post("/{tag_id}/edit")
async def rename_tag(
    request: Request,
    tag_id: int,
    name: str = Form(""),
    user: models.User = Depends(require_admin),
    _csrf: None = Depends(verify_csrf),
):
    tag = _get_tag_or_404(tag_id)
    name = name.strip()
    if not name:
        return _render_form(request, user, tag=tag, error="Name is required.",
                             name=name, status_code=400)
    try:
        models.rename_tag(tag_id, name)
    except sqlite3.IntegrityError:
        return _render_form(request, user, tag=tag, error=DUPLICATE_NAME_ERROR,
                             name=name, status_code=400)
    return console_shell.redirect_with_flash("/admin/tags", "Tag renamed.")


@router.get("/{tag_id}/delete")
def confirm_delete_tag(
    request: Request, tag_id: int, user: models.User = Depends(require_admin)
):
    tag = _get_tag_or_404(tag_id)
    context = console_shell.console_context(request, user)
    context.update({"title": "Delete tag?", "tag": tag})
    return templates.TemplateResponse(request, "admin/tags_delete.html", context)


@router.post("/{tag_id}/delete")
async def delete_tag(
    tag_id: int, user: models.User = Depends(require_admin),
    _csrf: None = Depends(verify_csrf),
):
    _get_tag_or_404(tag_id)
    models.delete_tag(tag_id)
    return console_shell.redirect_with_flash("/admin/tags", "Tag deleted.")
