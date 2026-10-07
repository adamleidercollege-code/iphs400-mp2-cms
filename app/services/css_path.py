"""The admin console's relative stylesheet path, computed per-request.

Split out of app/services/console_shell.py so app/routes/auth.py (login,
the pre-login "hello" screen) can use it without a circular import:
console_shell already imports ensure_csrf_token from auth, so auth can't
import console_shell back.
"""
from __future__ import annotations

from fastapi import Request


def css_path_for(request: Request) -> str:
    """The live admin server has no static-file route tied to a page's own
    nesting depth — /admin/posts/{id}/edit and /login sit at different
    depths — so this computes the right number of "../" to reach the one
    GET /style.css route (app/routes/console.py) from wherever `request`
    currently is. Same idea as app.publish's `_relative_link` for the
    static export, just computed per-request instead of precomputed per
    chain."""
    depth = len([s for s in request.url.path.strip("/").split("/") if s]) - 1
    return "../" * max(depth, 0) + "style.css"
