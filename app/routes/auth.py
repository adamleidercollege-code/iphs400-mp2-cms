"""Login, logout, and the reusable login-required / admin-required gate.

Session state lives in the signed session cookie (Starlette's SessionMiddleware,
itsdangerous-backed): `user_id` once logged in, and `csrf_token` for the
double-submit CSRF check on every state-changing form.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse

from app import models, settings
from app.services import csrf, passwords
from app.services.css_path import css_path_for

templates = Jinja2Templates(directory=str(settings.TEMPLATES))

router = APIRouter()

GENERIC_LOGIN_ERROR = "Incorrect email or password."


class LoginRequired(Exception):
    """Raised by `require_user` for an anonymous request; caught in app/main.py."""


class AdminRequired(Exception):
    """Raised by `require_admin` for a non-admin request; caught in app/main.py."""


class CsrfInvalid(Exception):
    """Raised by `verify_csrf` for a missing or wrong token; caught in app/main.py."""


def ensure_csrf_token(request: Request) -> str:
    """Make sure the session has a CSRF token, and return it for the form."""
    token = request.session.get("csrf_token")
    if not token:
        token = csrf.generate_token()
        request.session["csrf_token"] = token
    return token


async def verify_csrf(request: Request) -> None:
    form = await request.form()
    submitted = form.get("csrf_token")
    session_token = request.session.get("csrf_token")
    if not csrf.tokens_match(session_token, submitted):
        raise CsrfInvalid()


def get_current_user(request: Request) -> models.User | None:
    user_id = request.session.get("user_id")
    if user_id is None:
        return None
    user = models.get_user_by_id(user_id)
    if user is None or not user.active:
        return None
    return user


def require_user(request: Request) -> models.User:
    user = get_current_user(request)
    if user is None:
        raise LoginRequired()
    return user


def require_admin(user: models.User = Depends(require_user)) -> models.User:
    if user.role != "admin":
        raise AdminRequired()
    return user


@router.get("/login")
def login_form(request: Request):
    token = ensure_csrf_token(request)
    return templates.TemplateResponse(
        request, "admin/login.html",
        {"title": "Log in", "csrf_token": token, "error": None,
         "css_path": css_path_for(request)},
    )


@router.post("/login")
async def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    _csrf: None = Depends(verify_csrf),
):
    user = models.get_user_by_email(email)
    if user is None or not user.active or not passwords.verify_password(
        user.password_hash, password
    ):
        if user is None or not user.active:
            passwords.waste_time_like_a_verify(password)
        token = ensure_csrf_token(request)
        return templates.TemplateResponse(
            request, "admin/login.html",
            {"title": "Log in", "csrf_token": token, "error": GENERIC_LOGIN_ERROR,
             "css_path": css_path_for(request)},
            status_code=401,
        )

    request.session.clear()
    request.session["user_id"] = user.id
    request.session["csrf_token"] = csrf.generate_token()
    return RedirectResponse(url="/admin", status_code=303)


@router.post("/logout")
async def logout(request: Request, _csrf: None = Depends(verify_csrf)):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)


@router.get("/admin/_stub")
def admin_only_stub(request: Request, user: models.User = Depends(require_admin)):
    return templates.TemplateResponse(
        request, "admin/stub.html",
        {"title": "Admin-only stub", "user": user, "css_path": css_path_for(request)},
    )
