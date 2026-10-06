"""Staff console shell (T07, #8): the live-preview landing screen, Dashboard,
Content list, Pending queue, and Metrics.

Every route but the landing screen is admin-only (require_admin, same gate
as Pages and Accounts) — an Ambassador gets a 403, an anonymous request is
redirected to /login. Page hierarchy and Accounts are their own existing
routers (app/routes/pages.py, app/routes/accounts.py); this module only adds
the sidebar entries that point at them.

The landing screen (GET /admin) stays open to any logged-in user: Staff see
the live preview described below, an Ambassador sees the pre-T08 stub screen
until "My posts" (T08, #9) replaces it.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates

from app import models, settings
from app.routes.auth import ensure_csrf_token, get_current_user, require_admin
from app.routes.public import page_context

templates = Jinja2Templates(directory=str(settings.TEMPLATES))

router = APIRouter()

STATUS_CHOICES = ["draft", "pending", "published"]
TYPE_CHOICES = [("page", "Page"), ("post", "Post")]

SIDEBAR = [
    ("/admin/dashboard", "Dashboard"),
    ("/admin/content", "Content list"),
    ("/admin/pending", "Pending queue"),
    ("/admin/accounts", "Accounts"),
    ("/admin/pages", "Page hierarchy"),
    ("/admin/metrics", "Metrics"),
]


def _console_context(request: Request, user: models.User) -> dict:
    return {
        "user": user,
        "csrf_token": ensure_csrf_token(request),
        "sidebar": [{"href": href, "label": label} for href, label in SIDEBAR],
    }


@router.get("/admin")
def admin_home(request: Request, user: models.User | None = Depends(get_current_user)):
    if user is None or user.role != "admin":
        # Anonymous, or an Ambassador whose own landing screen ("My posts")
        # is T08's job, not this ticket's.
        csrf_token = ensure_csrf_token(request) if user else None
        return templates.TemplateResponse(
            request, "admin/hello.html",
            {"title": "Admin", "user": user, "csrf_token": csrf_token},
        )

    home_page = models.ensure_home_page()
    context = _console_context(request, user)
    context.update({"title": "Admin — Live preview", "preview": page_context(home_page)})
    return templates.TemplateResponse(request, "admin/home.html", context)


@router.get("/admin/dashboard")
def dashboard(request: Request, user: models.User = Depends(require_admin)):
    posts = models.list_all_posts()
    status_counts = {status: 0 for status in STATUS_CHOICES}
    for post in posts:
        status_counts[post.status] += 1

    level_counts: dict[int, int] = {}
    for page in models.list_all_pages():
        level = len(models.list_ancestors(page))
        level_counts[level] = level_counts.get(level, 0) + 1

    context = _console_context(request, user)
    context.update({
        "title": "Dashboard",
        "status_counts": [(status, status_counts[status]) for status in STATUS_CHOICES],
        "level_counts": sorted(level_counts.items()),
        "active_accounts": sum(1 for u in models.list_users() if u.active),
    })
    return templates.TemplateResponse(request, "admin/dashboard.html", context)


@router.get("/admin/content")
def content_list(
    request: Request,
    user: models.User = Depends(require_admin),
    status: str = "",
    kind: str = "",
):
    items = []
    if kind in ("", "page"):
        for page in models.list_all_pages():
            if status and page.status != status:
                continue
            items.append({
                "kind": "Page", "title": page.title, "status": page.status,
                "href": f"/admin/pages/{page.id}/edit",
            })
    if kind in ("", "post"):
        for post in models.list_all_posts():
            if status and post.status != status:
                continue
            items.append({
                "kind": "Post", "title": post.title, "status": post.status,
                "href": f"/admin/posts/{post.id}/edit",
            })

    context = _console_context(request, user)
    context.update({
        "title": "Content list",
        "items": items,
        "status_choices": STATUS_CHOICES,
        "type_choices": TYPE_CHOICES,
        "status_filter": status,
        "kind_filter": kind,
    })
    return templates.TemplateResponse(request, "admin/content_list.html", context)


@router.get("/admin/pending")
def pending_queue(request: Request, user: models.User = Depends(require_admin)):
    pending = sorted(
        (p for p in models.list_all_posts() if p.status == "pending"),
        key=lambda p: p.updated_at,
    )
    rows = []
    for post in pending:
        author = models.get_user_by_id(post.author_id) if post.author_id else None
        rows.append({
            "post": post,
            "author_name": author.display_name if author else "Unknown",
            "submitted_date": (post.updated_at or "")[:10],
            "edit_href": f"/admin/posts/{post.id}/edit",
        })

    context = _console_context(request, user)
    context.update({"title": "Pending queue", "rows": rows})
    return templates.TemplateResponse(request, "admin/pending_queue.html", context)


@router.get("/admin/metrics")
def metrics(request: Request, user: models.User = Depends(require_admin)):
    programs = [p for p in models.list_all_pages() if models.is_program_page(p)]
    rows = sorted(
        (
            {"program": program, "count": len(models.list_posts_by_program(program.id))}
            for program in programs
        ),
        key=lambda row: row["program"].title,
    )

    context = _console_context(request, user)
    context.update({"title": "Metrics", "rows": rows})
    return templates.TemplateResponse(request, "admin/metrics.html", context)
