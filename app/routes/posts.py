"""Post authoring: draft CRUD, Topic, and a sanitized Markdown preview.

Unlike Pages (admin-only), Post authoring is open to any active user
(require_user), with ownership enforced inside the route: an Ambassador
(editor) may only touch their own Post, and only while it is draft; a Staff
member (admin) may touch any Post, same as Pages. Submitting for review,
publishing, bouncing, and unpublishing are T04 (#5), not here.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse

from app import models, settings
from app.routes.auth import ensure_csrf_token, require_user, verify_csrf
from app.services import markdown

templates = Jinja2Templates(directory=str(settings.TEMPLATES))

router = APIRouter(prefix="/admin/posts")


def _get_program_or_404(program_id: int) -> models.Page:
    """Resolve program_id, rejecting up front if it isn't a Program-level
    Page — otherwise a user could fill out the whole new-post form before
    hitting the same rejection as a save-time error (models.create_post
    still checks this too, as the model layer's own guarantee)."""
    program = models.get_page_by_id(program_id)
    if program is None:
        raise HTTPException(status_code=404, detail="No such program page")
    if not models.is_program_page(program):
        raise HTTPException(status_code=400, detail="Not a Program-level page")
    return program


def _get_post_or_404(post_id: int) -> models.Post:
    post = models.get_post_by_id(post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="No such post")
    return post


def _authorize_post_write(user: models.User, post: models.Post) -> None:
    """Admin: any Post, any status. Editor: only their own, only while draft."""
    if user.role == "admin":
        return
    if post.author_id != user.id or post.status != "draft":
        raise HTTPException(status_code=403, detail="Forbidden")


def _render_form(
    request: Request,
    post: models.Post | None,
    program: models.Page,
    error: str | None = None,
    title: str = "",
    body: str = "",
    topic: str = "general",
):
    token = ensure_csrf_token(request)
    return templates.TemplateResponse(
        request, "admin/posts_form.html",
        {
            "title": "Edit post" if post else "New post",
            "post": post,
            "program": program,
            "csrf_token": token,
            "error": error,
            "form_title": title,
            "form_body": body,
            "form_topic": topic,
            "preview_html": markdown.render(body),
            "topics": models.TOPIC_CHOICES,
        },
    )


@router.get("")
def list_posts(
    request: Request, program_id: int, user: models.User = Depends(require_user)
):
    program = _get_program_or_404(program_id)
    posts = models.list_posts_by_program(program_id)
    if user.role != "admin":
        posts = [p for p in posts if p.author_id == user.id]
    token = ensure_csrf_token(request)
    return templates.TemplateResponse(
        request, "admin/posts_list.html",
        {"title": "Posts", "program": program, "posts": posts, "csrf_token": token},
    )


@router.get("/new")
def new_post_form(
    request: Request, program_id: int, user: models.User = Depends(require_user)
):
    program = _get_program_or_404(program_id)
    return _render_form(request, post=None, program=program)


@router.post("/new")
async def create_post(
    request: Request,
    program_id: int = Form(...),
    title: str = Form(""),
    body: str = Form(""),
    topic: str = Form("general"),
    action: str = Form("save"),
    user: models.User = Depends(require_user),
    _csrf: None = Depends(verify_csrf),
):
    program = _get_program_or_404(program_id)
    if action == "preview":
        return _render_form(request, post=None, program=program,
                             title=title, body=body, topic=topic)
    if not title.strip():
        return _render_form(request, post=None, program=program,
                             error="Title is required.", title=title, body=body, topic=topic)
    try:
        models.create_post(
            program_id=program_id, title=title, body=body, topic=topic, author_id=user.id,
        )
    except ValueError as exc:
        return _render_form(request, post=None, program=program,
                             error=str(exc), title=title, body=body, topic=topic)
    return RedirectResponse(url=f"/admin/posts?program_id={program_id}", status_code=303)


@router.get("/{post_id}/edit")
def edit_post_form(
    request: Request, post_id: int, user: models.User = Depends(require_user)
):
    post = _get_post_or_404(post_id)
    _authorize_post_write(user, post)
    program = _get_program_or_404(post.program_id)
    return _render_form(request, post=post, program=program,
                         title=post.title, body=post.body, topic=post.topic)


@router.post("/{post_id}/edit")
async def update_post(
    request: Request,
    post_id: int,
    title: str = Form(""),
    body: str = Form(""),
    topic: str = Form("general"),
    action: str = Form("save"),
    user: models.User = Depends(require_user),
    _csrf: None = Depends(verify_csrf),
):
    post = _get_post_or_404(post_id)
    _authorize_post_write(user, post)
    program = _get_program_or_404(post.program_id)
    if action == "preview":
        return _render_form(request, post=post, program=program,
                             title=title, body=body, topic=topic)
    if not title.strip():
        return _render_form(request, post=post, program=program,
                             error="Title is required.", title=title, body=body, topic=topic)
    try:
        models.update_post(post_id, title=title, body=body, topic=topic)
    except ValueError as exc:
        return _render_form(request, post=post, program=program,
                             error=str(exc), title=title, body=body, topic=topic)
    return RedirectResponse(url=f"/admin/posts?program_id={program.id}", status_code=303)


@router.get("/{post_id}/delete")
def confirm_delete_post(
    request: Request, post_id: int, user: models.User = Depends(require_user)
):
    post = _get_post_or_404(post_id)
    _authorize_post_write(user, post)
    token = ensure_csrf_token(request)
    return templates.TemplateResponse(
        request, "admin/posts_delete.html",
        {"title": "Delete post?", "post": post, "csrf_token": token},
    )


@router.post("/{post_id}/delete")
async def delete_post(
    post_id: int, user: models.User = Depends(require_user),
    _csrf: None = Depends(verify_csrf),
):
    post = _get_post_or_404(post_id)
    _authorize_post_write(user, post)
    program_id = post.program_id
    models.delete_post(post_id)
    return RedirectResponse(url=f"/admin/posts?program_id={program_id}", status_code=303)
