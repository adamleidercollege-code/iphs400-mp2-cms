"""Post authoring: draft CRUD, Topic, a sanitized Markdown preview, and the
ADR-004 review-gate state machine (T04, #5).

Unlike Pages (admin-only), Post authoring is open to any active user
(require_user), with ownership enforced inside the route: an Ambassador
(editor) may only touch their own Post, and only while it is draft; a Staff
member (admin) may touch any Post, same as Pages. The submit/publish/bounce/
unpublish transitions delegate every allow/deny decision to
app.services.review_gate, so this module just resolves the Post, asks the
service whether the action is allowed, and persists the result.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.templating import Jinja2Templates

from app import models, settings
from app.routes.auth import require_user, verify_csrf
from app.services import console_shell, markdown, media_store, post_view, review_gate

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


def _existing_tag_ids(tag_ids: list[int]) -> list[int]:
    """Drop any `tag_ids` value that isn't a real Tag — a submitted form
    always lists only existing tags as checkboxes, but a tampered or stale
    request could send one that's since been deleted; silently dropping it
    (rather than 500ing on the tags.post_tags foreign key) is enough, since
    there's nothing useful to tell the submitter about a tag they can't see."""
    valid = {t.id for t in models.list_tags()}
    return [tag_id for tag_id in tag_ids if tag_id in valid]


def _authorize_post_write(user: models.User, post: models.Post) -> None:
    """Admin: any Post, any status. Editor: only their own, only while draft."""
    if user.role == "admin":
        return
    if post.author_id != user.id or post.status != "draft":
        raise HTTPException(status_code=403, detail="Forbidden")


def _apply_transition(user: models.User, post: models.Post, action: str) -> models.Post:
    """Ask review_gate whether `action` is allowed, then persist its answer.

    review_gate.transition raises ValueError -> 403 (not allowed at all).
    models.set_post_status raises StatusConflict -> 409 (it *was* allowed
    against the status we read, but another request changed it first).
    """
    is_author = post.author_id == user.id
    try:
        new_status = review_gate.transition(post.status, action, user.role, is_author)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    try:
        return models.set_post_status(post.id, from_status=post.status, to_status=new_status)
    except models.StatusConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))


def _render_form(
    request: Request,
    user: models.User,
    post: models.Post | None,
    program: models.Page,
    error: str | None = None,
    title: str = "",
    body: str = "",
    topic: str = "general",
    tag_ids: list[int] | None = None,
):
    selected_tag_ids = (
        tag_ids if tag_ids is not None
        else [t.id for t in models.get_tags_for_post(post.id)] if post else []
    )
    cover = (
        post_view.media_cover(post.cover_media_id, post_view.media_href_for("/"))
        if post else None
    )
    preview_media_href = (
        post_view.post_body_media_href_for(post, "/", text=body)
        if post else (lambda _media_id: "#")
    )
    context = console_shell.console_context(request, user)
    context.update({
        "title": "Edit post" if post else "New post",
        "post": post,
        "program": program,
        "error": error,
        "form_title": title,
        "form_body": body,
        "form_topic": topic,
        "form_tag_ids": selected_tag_ids,
        "preview_html": markdown.render(body, media_href=preview_media_href),
        "topics": models.TOPIC_CHOICES,
        "tags": models.list_tags(),
        "cover": cover,
        "just_added": _just_added_media(request),
        "added_kind": request.query_params.get("added_kind"),
    })
    return templates.TemplateResponse(request, "admin/posts_form.html", context)


def _just_added_media(request: Request) -> dict | None:
    """The Media a redirect back from a successful upload just added
    (console_shell.redirect_with_flash's `added_media_id`) — {href, alt}
    for the small thumbnail next to that upload section's confirmation."""
    added_media_id = request.query_params.get("added_media_id")
    if not added_media_id or not added_media_id.isdigit():
        return None
    media = models.get_media_by_id(int(added_media_id))
    if media is None:
        return None
    return {"href": f"/media/{media.filename}", "alt": media.alt_text}


@router.get("")
def list_posts(
    request: Request, program_id: int, user: models.User = Depends(require_user)
):
    program = _get_program_or_404(program_id)
    posts = models.list_posts_by_program(program_id)
    if user.role != "admin":
        posts = [p for p in posts if p.author_id == user.id]
    posts_with_actions = [
        (
            post,
            [
                (action, review_gate.ACTION_LABELS[action])
                for action in review_gate.available_actions(
                    post.status, user.role, post.author_id == user.id
                )
            ],
        )
        for post in posts
    ]
    context = console_shell.console_context(request, user)
    context.update({"title": "Posts", "program": program,
                     "posts_with_actions": posts_with_actions})
    return templates.TemplateResponse(request, "admin/posts_list.html", context)


@router.get("/new")
def new_post_form(
    request: Request, program_id: int, user: models.User = Depends(require_user)
):
    program = _get_program_or_404(program_id)
    return _render_form(request, user, post=None, program=program)


@router.post("/new")
async def create_post(
    request: Request,
    program_id: int = Form(...),
    title: str = Form(""),
    body: str = Form(""),
    topic: str = Form("general"),
    tag_ids: list[int] = Form([]),
    action: str = Form("save"),
    user: models.User = Depends(require_user),
    _csrf: None = Depends(verify_csrf),
):
    program = _get_program_or_404(program_id)
    if action == "preview":
        return _render_form(request, user, post=None, program=program,
                             title=title, body=body, topic=topic, tag_ids=tag_ids)
    if not title.strip():
        return _render_form(request, user, post=None, program=program,
                             error="Title is required.", title=title, body=body,
                             topic=topic, tag_ids=tag_ids)
    try:
        post = models.create_post(
            program_id=program_id, title=title, body=body, topic=topic, author_id=user.id,
        )
    except ValueError as exc:
        return _render_form(request, user, post=None, program=program,
                             error=str(exc), title=title, body=body,
                             topic=topic, tag_ids=tag_ids)
    models.set_post_tags(post.id, _existing_tag_ids(tag_ids))
    return console_shell.redirect_with_flash(
        f"/admin/posts?program_id={program_id}", "Post created.")


@router.get("/{post_id}/edit")
def edit_post_form(
    request: Request, post_id: int, user: models.User = Depends(require_user)
):
    post = _get_post_or_404(post_id)
    _authorize_post_write(user, post)
    program = _get_program_or_404(post.program_id)
    return _render_form(request, user, post=post, program=program,
                         title=post.title, body=post.body, topic=post.topic)


@router.post("/{post_id}/edit")
async def update_post(
    request: Request,
    post_id: int,
    title: str = Form(""),
    body: str = Form(""),
    topic: str = Form("general"),
    tag_ids: list[int] = Form([]),
    action: str = Form("save"),
    user: models.User = Depends(require_user),
    _csrf: None = Depends(verify_csrf),
):
    post = _get_post_or_404(post_id)
    _authorize_post_write(user, post)
    program = _get_program_or_404(post.program_id)
    if action == "preview":
        return _render_form(request, user, post=post, program=program,
                             title=title, body=body, topic=topic, tag_ids=tag_ids)
    if not title.strip():
        return _render_form(request, user, post=post, program=program,
                             error="Title is required.", title=title, body=body,
                             topic=topic, tag_ids=tag_ids)
    try:
        models.update_post(post_id, title=title, body=body, topic=topic)
    except ValueError as exc:
        return _render_form(request, user, post=post, program=program,
                             error=str(exc), title=title, body=body,
                             topic=topic, tag_ids=tag_ids)
    models.set_post_tags(post_id, _existing_tag_ids(tag_ids))
    return console_shell.redirect_with_flash(
        f"/admin/posts?program_id={program.id}", "Post saved.")


@router.get("/{post_id}/delete")
def confirm_delete_post(
    request: Request, post_id: int, user: models.User = Depends(require_user)
):
    post = _get_post_or_404(post_id)
    _authorize_post_write(user, post)
    context = console_shell.console_context(request, user)
    context.update({"title": "Delete post?", "post": post})
    return templates.TemplateResponse(request, "admin/posts_delete.html", context)


@router.post("/{post_id}/delete")
async def delete_post(
    post_id: int, user: models.User = Depends(require_user),
    _csrf: None = Depends(verify_csrf),
):
    post = _get_post_or_404(post_id)
    _authorize_post_write(user, post)
    program_id = post.program_id
    models.delete_post(post_id)
    return console_shell.redirect_with_flash(
        f"/admin/posts?program_id={program_id}", "Post deleted.")


@router.post("/{post_id}/submit")
async def submit_post(
    post_id: int, user: models.User = Depends(require_user),
    _csrf: None = Depends(verify_csrf),
):
    post = _get_post_or_404(post_id)
    _apply_transition(user, post, "submit")
    return console_shell.redirect_with_flash(
        f"/admin/posts?program_id={post.program_id}", "Post submitted for review.")


@router.post("/{post_id}/publish")
async def publish_post(
    post_id: int, user: models.User = Depends(require_user),
    _csrf: None = Depends(verify_csrf),
):
    post = _get_post_or_404(post_id)
    _apply_transition(user, post, "publish")
    return console_shell.redirect_with_flash(
        f"/admin/posts?program_id={post.program_id}", "Post published.")


@router.post("/{post_id}/bounce")
async def bounce_post(
    post_id: int, user: models.User = Depends(require_user),
    _csrf: None = Depends(verify_csrf),
):
    post = _get_post_or_404(post_id)
    _apply_transition(user, post, "bounce")
    return console_shell.redirect_with_flash(
        f"/admin/posts?program_id={post.program_id}", "Post sent back to draft.")


@router.post("/{post_id}/unpublish")
async def unpublish_post(
    post_id: int, user: models.User = Depends(require_user),
    _csrf: None = Depends(verify_csrf),
):
    post = _get_post_or_404(post_id)
    _apply_transition(user, post, "unpublish")
    return console_shell.redirect_with_flash(
        f"/admin/posts?program_id={post.program_id}", "Post unpublished.")


@router.post("/{post_id}/cover")
async def set_post_cover(
    request: Request,
    post_id: int,
    image: UploadFile = File(...),
    alt_text: str = Form(""),
    user: models.User = Depends(require_user),
    _csrf: None = Depends(verify_csrf),
):
    post = _get_post_or_404(post_id)
    _authorize_post_write(user, post)
    program = _get_program_or_404(post.program_id)
    alt_text = alt_text.strip()
    if not alt_text:
        return _render_form(request, user, post=post, program=program,
                             error="Alt text is required for the cover image.",
                             title=post.title, body=post.body, topic=post.topic)
    data = await image.read()
    try:
        filename, content_type, size = media_store.save_upload(data, user.id)
    except media_store.UploadRejected as exc:
        return _render_form(request, user, post=post, program=program,
                             error=str(exc), title=post.title, body=post.body,
                             topic=post.topic)
    media = models.create_media(filename=filename, content_type=content_type,
                                 size=size, alt_text=alt_text, uploaded_by=user.id)
    models.set_post_cover(post.id, media.id)
    return console_shell.redirect_with_flash(
        f"/admin/posts/{post.id}/edit", "Cover image set.",
        fragment="cover-section", added_kind="cover", added_media_id=str(media.id))


@router.post("/{post_id}/images")
async def add_post_image(
    request: Request,
    post_id: int,
    image: UploadFile = File(...),
    alt_text: str = Form(""),
    user: models.User = Depends(require_user),
    _csrf: None = Depends(verify_csrf),
):
    post = _get_post_or_404(post_id)
    _authorize_post_write(user, post)
    program = _get_program_or_404(post.program_id)
    alt_text = alt_text.strip()
    if not alt_text:
        return _render_form(request, user, post=post, program=program,
                             error="Alt text is required before an image can be added.",
                             title=post.title, body=post.body, topic=post.topic)
    data = await image.read()
    try:
        filename, content_type, size = media_store.save_upload(data, user.id)
    except media_store.UploadRejected as exc:
        return _render_form(request, user, post=post, program=program,
                             error=str(exc), title=post.title, body=post.body,
                             topic=post.topic)
    media = models.create_media(filename=filename, content_type=content_type,
                                 size=size, alt_text=alt_text, uploaded_by=user.id,
                                 post_id=post.id)
    new_body = post.body.rstrip() + f"\n\n![{alt_text}](media/{media.id})\n"
    models.update_post(post_id, title=post.title, body=new_body, topic=post.topic)
    return console_shell.redirect_with_flash(
        f"/admin/posts/{post.id}/edit", "Image added to the post.",
        fragment="images-section", added_kind="image", added_media_id=str(media.id))
