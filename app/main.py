"""The FastAPI application.

T00 (already done): the admin console answers at /admin and the public site
answers at /. That is the whole skeleton — it exists so you can prove the stack
runs before you build anything on it.

Add your routes in their own modules (app/routes/posts.py and so on) and include
them here. Keep this file small.
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

from app import db, settings
from app.routes import accounts, auth, console, media, pages, posts, public, tags
from app.routes.auth import AdminRequired, CsrfInvalid, LoginRequired, get_current_user, templates
from app.services.css_path import css_path_for


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
        return templates.TemplateResponse(
            request, "admin/forbidden.html",
            {"title": "Staff only", "user": get_current_user(request),
             "css_path": css_path_for(request), "my_posts_href": "/admin"},
            status_code=403,
        )

    @app.exception_handler(CsrfInvalid)
    def _csrf_invalid(request: Request, exc: CsrfInvalid):
        return PlainTextResponse("Forbidden: missing or invalid CSRF token", status_code=403)

    app.include_router(auth.router)
    app.include_router(pages.router)
    app.include_router(posts.router)
    app.include_router(accounts.router)
    app.include_router(tags.router)
    app.include_router(console.router)
    app.include_router(media.router)

    # Catch-all last: the live public site, read straight from the database —
    # the admin console's "preview" of what `cms publish` will later export.
    app.include_router(public.router)
    return app


app = create_app()
