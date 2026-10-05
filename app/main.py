"""The FastAPI application.

T00 (already done): the admin console answers at /admin and the public site
answers at /. That is the whole skeleton — it exists so you can prove the stack
runs before you build anything on it.

Add your routes in their own modules (app/routes/posts.py and so on) and include
them here. Keep this file small.
"""
from __future__ import annotations

from fastapi import Depends, FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import PlainTextResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

from app import db, models, settings
from app.routes import auth, pages, posts, public
from app.routes.auth import (
    AdminRequired,
    CsrfInvalid,
    LoginRequired,
    ensure_csrf_token,
    get_current_user,
)

templates = Jinja2Templates(directory=str(settings.TEMPLATES))


def create_app() -> FastAPI:
    db.init_db()
    app = FastAPI(title="IPHS 400 MP2 CMS")
    app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY,
                        session_cookie="cms_session")

    @app.exception_handler(LoginRequired)
    def _login_required(request: Request, exc: LoginRequired):
        return RedirectResponse(url="/login", status_code=303)

    @app.exception_handler(AdminRequired)
    def _admin_required(request: Request, exc: AdminRequired):
        return PlainTextResponse("Forbidden", status_code=403)

    @app.exception_handler(CsrfInvalid)
    def _csrf_invalid(request: Request, exc: CsrfInvalid):
        return PlainTextResponse("Forbidden: missing or invalid CSRF token", status_code=403)

    app.include_router(auth.router)
    app.include_router(pages.router)
    app.include_router(posts.router)

    @app.get("/admin")
    def admin_home(request: Request, user: models.User | None = Depends(get_current_user)):
        csrf_token = ensure_csrf_token(request) if user else None
        return templates.TemplateResponse(
            request, "admin/hello.html",
            {"title": "Admin", "user": user, "csrf_token": csrf_token},
        )

    # Catch-all last: the live public site, read straight from the database —
    # the admin console's "preview" of what `cms publish` will later export.
    app.include_router(public.router)

    # Your ticket work plugs in here, e.g.
    #   from app.routes import posts
    #   app.include_router(posts.router)
    return app


app = create_app()
