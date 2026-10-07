"""Account management: create a user, assign a role, activate/deactivate —
Staff-only (require_admin, same gate as Pages — an Ambassador is blocked from
every route in this module, an anonymous request redirected to /login).

Deactivation applies the role-specific cascade from
app.services.deactivation via models.deactivate_user; this module just
resolves the user and persists the result.
"""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.templating import Jinja2Templates

from app import models, settings
from app.routes.auth import require_admin, verify_csrf
from app.services import console_shell

templates = Jinja2Templates(directory=str(settings.TEMPLATES))

router = APIRouter(prefix="/admin/accounts")

ROLE_CHOICES = [("admin", "Staff"), ("editor", "Ambassador")]
ROLE_VALUES = {value for value, _label in ROLE_CHOICES}


def _get_user_or_404(user_id: int) -> models.User:
    user = models.get_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="No such user")
    return user


def _render_new_form(
    request: Request, user: models.User, error: str | None, email: str,
    display_name: str, role: str, status_code: int = 200,
):
    context = console_shell.console_context(request, user)
    context.update({
        "title": "New account",
        "error": error,
        "roles": ROLE_CHOICES,
        "form_email": email,
        "form_display_name": display_name,
        "form_role": role,
    })
    return templates.TemplateResponse(
        request, "admin/accounts_form.html", context, status_code=status_code,
    )


@router.get("")
def list_accounts(request: Request, user: models.User = Depends(require_admin)):
    context = console_shell.console_context(request, user)
    context.update({"title": "Accounts", "users": models.list_users()})
    return templates.TemplateResponse(request, "admin/accounts_list.html", context)


@router.get("/new")
def new_account_form(request: Request, user: models.User = Depends(require_admin)):
    return _render_new_form(request, user, error=None, email="", display_name="", role="editor")


@router.get("/{user_id}/edit")
def edit_account_form(
    request: Request, user_id: int, user: models.User = Depends(require_admin)
):
    target = _get_user_or_404(user_id)
    context = console_shell.console_context(request, user)
    context.update({"title": "Change role", "target": target, "roles": ROLE_CHOICES})
    return templates.TemplateResponse(request, "admin/accounts_edit.html", context)


@router.post("/{user_id}/edit")
async def update_account_role(
    user_id: int,
    role: str = Form(...),
    user: models.User = Depends(require_admin),
    _csrf: None = Depends(verify_csrf),
):
    _get_user_or_404(user_id)
    if role not in ROLE_VALUES:
        raise HTTPException(status_code=400, detail="Invalid role")
    models.set_user_role(user_id, role)
    return console_shell.redirect_with_flash("/admin/accounts", "Role updated.")


@router.post("/new")
async def create_account(
    request: Request,
    email: str = Form(""),
    display_name: str = Form(""),
    password: str = Form(""),
    role: str = Form("editor"),
    user: models.User = Depends(require_admin),
    _csrf: None = Depends(verify_csrf),
):
    if role not in ROLE_VALUES:
        raise HTTPException(status_code=400, detail="Invalid role")
    if not email.strip() or not display_name.strip() or not password:
        return _render_new_form(
            request, user, error="Email, display name, and password are all required.",
            email=email, display_name=display_name, role=role, status_code=400,
        )
    try:
        models.create_user(
            email=email, password=password, role=role, display_name=display_name,
        )
    except sqlite3.IntegrityError:
        return _render_new_form(
            request, user, error="An account with that email already exists.",
            email=email, display_name=display_name, role=role, status_code=400,
        )
    return console_shell.redirect_with_flash("/admin/accounts", "Account created.")


@router.post("/{user_id}/deactivate")
async def deactivate_account(
    user_id: int, user: models.User = Depends(require_admin),
    _csrf: None = Depends(verify_csrf),
):
    _get_user_or_404(user_id)
    models.deactivate_user(user_id)
    return console_shell.redirect_with_flash("/admin/accounts", "Account deactivated.")


@router.post("/{user_id}/reactivate")
async def reactivate_account(
    user_id: int, user: models.User = Depends(require_admin),
    _csrf: None = Depends(verify_csrf),
):
    _get_user_or_404(user_id)
    models.reactivate_user(user_id)
    return console_shell.redirect_with_flash("/admin/accounts", "Account reactivated.")
