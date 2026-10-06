"""T06: User management and the deactivation cascade."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from app import models
from app.services import deactivation
from tests.conftest import _csrf_token_from

_ROOT = Path(__file__).resolve().parents[1]


# --- Services seam: pure, no HTTP or DB -------------------------------------


@pytest.mark.parametrize(
    "role,expected", [("editor", True), ("admin", False)]
)
def test_should_delete_drafts_is_role_specific(role, expected):
    assert deactivation.should_delete_drafts(role) is expected


# --- Models seam: the cascade itself ----------------------------------------


def _seed_program(author_id: int) -> models.Page:
    home = models.ensure_home_page()
    continent = models.create_page(home.id, "Asia", "", False, author_id)
    country = models.create_page(continent.id, "Japan", "", False, author_id)
    return models.create_page(country.id, "Kyoto Exchange", "", False, author_id)


def test_deactivating_an_ambassador_deletes_their_draft_posts(client):
    admin = models.get_user_by_email("admin@example.test")
    ambassador = models.create_user(
        email="leaving-student@example.test", password="pw",
        role="editor", display_name="Leaving Student",
    )
    program = _seed_program(admin.id)
    draft = models.create_post(program.id, "My Draft", "body", "housing", ambassador.id)

    models.deactivate_user(ambassador.id)

    assert models.get_post_by_id(draft.id) is None
    assert models.get_user_by_id(ambassador.id).active is False


def test_deactivating_a_staff_member_leaves_their_drafts_untouched(client):
    admin = models.get_user_by_email("admin@example.test")
    leaving_staff = models.create_user(
        email="leaving-staff@example.test", password="pw",
        role="admin", display_name="Leaving Staff",
    )
    program = _seed_program(admin.id)
    draft = models.create_post(program.id, "Ongoing Work", "body", "housing", leaving_staff.id)

    models.deactivate_user(leaving_staff.id)

    kept = models.get_post_by_id(draft.id)
    assert kept is not None
    assert kept.status == "draft"
    assert models.get_user_by_id(leaving_staff.id).active is False


@pytest.mark.parametrize("role", ["editor", "admin"])
def test_deactivation_leaves_pending_and_published_posts_alone(client, role):
    admin = models.get_user_by_email("admin@example.test")
    author = models.create_user(
        email=f"author-{role}@example.test", password="pw",
        role=role, display_name="Author", active=True,
    )
    program = _seed_program(admin.id)
    pending = models.create_post(program.id, "Pending Post", "body", "housing", author.id)
    models.set_post_status(pending.id, from_status="draft", to_status="pending")
    published = models.create_post(program.id, "Published Post", "body", "housing", author.id)
    models.set_post_status(published.id, from_status="draft", to_status="pending")
    models.set_post_status(published.id, from_status="pending", to_status="published")

    models.deactivate_user(author.id)

    assert models.get_post_by_id(pending.id).status == "pending"
    published_after = models.get_post_by_id(published.id)
    assert published_after.status == "published"
    assert published_after.author_id == author.id


def test_set_user_role_changes_an_existing_users_role(client):
    ambassador = models.create_user(
        email="promote-me@example.test", password="pw",
        role="editor", display_name="Promote Me",
    )
    updated = models.set_user_role(ambassador.id, "admin")
    assert updated.role == "admin"
    assert models.get_user_by_id(ambassador.id).role == "admin"


def test_set_user_role_rejects_an_invalid_role(client):
    user = models.create_user(
        email="bad-role@example.test", password="pw",
        role="editor", display_name="Bad Role",
    )
    with pytest.raises(ValueError):
        models.set_user_role(user.id, "superadmin")
    assert models.get_user_by_id(user.id).role == "editor"


def test_reactivate_user_restores_active_flag(client):
    ambassador = models.create_user(
        email="back-again@example.test", password="pw",
        role="editor", display_name="Back Again",
    )
    models.deactivate_user(ambassador.id)
    assert models.get_user_by_id(ambassador.id).active is False

    models.reactivate_user(ambassador.id)
    assert models.get_user_by_id(ambassador.id).active is True


# --- HTTP seam ---------------------------------------------------------------


def test_staff_creates_a_user_and_assigns_a_role(client_as):
    admin_c = client_as("admin")
    page = admin_c.get("/admin/accounts/new")
    assert page.status_code == 200
    token = _csrf_token_from(page.text)
    response = admin_c.post(
        "/admin/accounts/new",
        data={
            "email": "new-ambassador@example.test",
            "display_name": "New Ambassador",
            "password": "a-fine-password",
            "role": "editor",
            "csrf_token": token,
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    created = models.get_user_by_email("new-ambassador@example.test")
    assert created is not None
    assert created.role == "editor"
    assert created.active is True


def test_staff_deactivates_and_reactivates_a_user(client_as):
    admin_c = client_as("admin")
    target = models.create_user(
        email="toggle@example.test", password="pw",
        role="editor", display_name="Toggle Me",
    )
    list_page = admin_c.get("/admin/accounts")
    token = _csrf_token_from(list_page.text)
    response = admin_c.post(
        f"/admin/accounts/{target.id}/deactivate",
        data={"csrf_token": token}, follow_redirects=False,
    )
    assert response.status_code == 303
    assert models.get_user_by_id(target.id).active is False

    list_page = admin_c.get("/admin/accounts")
    token = _csrf_token_from(list_page.text)
    response = admin_c.post(
        f"/admin/accounts/{target.id}/reactivate",
        data={"csrf_token": token}, follow_redirects=False,
    )
    assert response.status_code == 303
    assert models.get_user_by_id(target.id).active is True


def test_staff_changes_an_existing_users_role_via_the_edit_screen(client_as):
    admin_c = client_as("admin")
    target = models.create_user(
        email="change-role@example.test", password="pw",
        role="editor", display_name="Change Role",
    )
    edit_page = admin_c.get(f"/admin/accounts/{target.id}/edit")
    assert edit_page.status_code == 200
    token = _csrf_token_from(edit_page.text)
    response = admin_c.post(
        f"/admin/accounts/{target.id}/edit",
        data={"role": "admin", "csrf_token": token},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert models.get_user_by_id(target.id).role == "admin"


def test_ambassador_is_blocked_from_every_accounts_route(client_as):
    editor_c = client_as("editor")
    target = models.create_user(
        email="victim@example.test", password="pw",
        role="editor", display_name="Victim",
    )
    assert editor_c.get("/admin/accounts").status_code == 403
    assert editor_c.get("/admin/accounts/new").status_code == 403
    assert editor_c.post("/admin/accounts/new", data={}).status_code == 403
    assert editor_c.get(f"/admin/accounts/{target.id}/edit").status_code == 403
    assert editor_c.post(f"/admin/accounts/{target.id}/edit",
                          data={"role": "admin"}).status_code == 403
    assert editor_c.post(f"/admin/accounts/{target.id}/deactivate",
                          data={}).status_code == 403
    assert editor_c.post(f"/admin/accounts/{target.id}/reactivate",
                          data={}).status_code == 403
    # No self-escalation even on their own account.
    editor = models.get_user_by_email("editor@example.test")
    assert editor_c.post(f"/admin/accounts/{editor.id}/edit",
                          data={"role": "admin"}).status_code == 403
    assert models.get_user_by_id(editor.id).role == "editor"


def test_anonymous_request_is_redirected_to_login(client):
    response = client.get("/admin/accounts", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_published_post_keeps_its_byline_after_author_deactivated(client_as):
    admin_c = client_as("admin")
    admin = models.get_user_by_email("admin@example.test")
    ambassador = models.create_user(
        email="byline-author@example.test", password="pw",
        role="editor", display_name="Byline Author",
    )
    program = _seed_program(admin.id)
    post = models.create_post(program.id, "A Great Post", "body", "housing", ambassador.id)
    models.set_post_status(post.id, from_status="draft", to_status="pending")
    models.set_post_status(post.id, from_status="pending", to_status="published")

    models.deactivate_user(ambassador.id)

    home = models.ensure_home_page()
    chain = [p.slug for p in models.list_ancestors(program) if p.id != home.id]
    chain.append(program.slug)
    chain.append(post.slug)
    url = "/" + "/".join(chain) + "/"
    response = admin_c.get(url)
    assert response.status_code == 200
    assert "Byline Author" in response.text


def test_duplicate_email_is_rejected_with_a_friendly_error(client_as):
    admin_c = client_as("admin")
    page = admin_c.get("/admin/accounts/new")
    token = _csrf_token_from(page.text)
    response = admin_c.post(
        "/admin/accounts/new",
        data={
            "email": "admin@example.test",  # already seeded
            "display_name": "Duplicate",
            "password": "whatever",
            "role": "admin",
            "csrf_token": token,
        },
    )
    assert response.status_code == 400
    assert "already exists" in response.text


# --- scripts/seed_demo.py ----------------------------------------------------


def _load_seed_demo():
    spec = importlib.util.spec_from_file_location(
        "seed_demo", _ROOT / "scripts" / "seed_demo.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_seed_demo_seeds_deactivated_users_showing_the_cascade(client):
    seed_demo = _load_seed_demo()
    admin = models.get_user_by_email("admin@example.test")
    editor = models.get_user_by_email("editor@example.test")
    programs = seed_demo._seed_pages(admin.id)
    seed_demo._seed_posts(programs, editor.id)
    seed_demo._seed_deactivated_users_with_drafts(programs)

    deactivated_ambassador = models.get_user_by_email("deactivated-ambassador@example.test")
    assert deactivated_ambassador is not None
    assert deactivated_ambassador.active is False
    assert models.list_posts_by_author(deactivated_ambassador.id) == []

    deactivated_staff = models.get_user_by_email("deactivated-staff@example.test")
    assert deactivated_staff is not None
    assert deactivated_staff.active is False
    staff_posts = models.list_posts_by_author(deactivated_staff.id)
    assert len(staff_posts) == 1
    assert staff_posts[0].status == "draft"
