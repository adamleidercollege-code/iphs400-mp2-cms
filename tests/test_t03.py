"""T03: Posts — draft authoring, Topic, and a Markdown preview."""
from __future__ import annotations

import importlib.util
from pathlib import Path

from app import models
from tests.conftest import _csrf_token_from

_ROOT = Path(__file__).resolve().parents[1]


def _load_seed_demo():
    """scripts/ isn't a package (see tests/test_usage_report.py for prior art)."""
    spec = importlib.util.spec_from_file_location(
        "seed_demo", _ROOT / "scripts" / "seed_demo.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _admin_csrf(c) -> str:
    return _csrf_token_from(c.get("/admin").text)


def _seed_program(parent_author_id: int) -> models.Page:
    """Home -> Continent -> Country -> Program, matching the spec's
    "Program is three levels below Home" field definition."""
    home = models.ensure_home_page()
    continent = models.create_page(home.id, "Asia", "", False, parent_author_id)
    country = models.create_page(continent.id, "Japan", "", False, parent_author_id)
    return models.create_page(country.id, "Kyoto Exchange", "", False, parent_author_id)


def _create_post(c, program_id, title, body="Hello **world**", topic="housing"):
    page = c.get(f"/admin/posts/new?program_id={program_id}")
    token = _csrf_token_from(page.text)
    return c.post(
        "/admin/posts/new",
        data={"program_id": str(program_id), "title": title, "body": body,
              "topic": topic, "action": "save", "csrf_token": token},
        follow_redirects=False,
    )


def test_editor_creates_edits_deletes_own_draft_post(client_as):
    c = client_as("editor")
    admin = models.get_user_by_email("admin@example.test")
    program = _seed_program(admin.id)

    response = _create_post(c, program.id, "My First Week")
    assert response.status_code == 303

    post = models.list_posts_by_program(program.id)[0]
    assert post.title == "My First Week"
    assert post.slug == "my-first-week"
    assert post.topic == "housing"
    assert post.status == "draft"
    editor = models.get_user_by_email("editor@example.test")
    assert post.author_id == editor.id

    edit_page = c.get(f"/admin/posts/{post.id}/edit")
    assert edit_page.status_code == 200
    token = _csrf_token_from(edit_page.text)
    c.post(f"/admin/posts/{post.id}/edit",
           data={"title": "Renamed Post", "body": "x", "topic": "meals",
                 "action": "save", "csrf_token": token},
           follow_redirects=False)
    renamed = models.get_post_by_id(post.id)
    assert renamed.title == "Renamed Post"
    assert renamed.slug == "renamed-post"
    assert renamed.topic == "meals"

    confirm = c.get(f"/admin/posts/{post.id}/delete")
    assert confirm.status_code == 200
    assert "are you sure" in confirm.text.lower()
    token = _csrf_token_from(confirm.text)
    response = c.post(f"/admin/posts/{post.id}/delete",
                       data={"csrf_token": token}, follow_redirects=False)
    assert response.status_code == 303
    assert models.get_post_by_id(post.id) is None


def test_preview_shows_sanitized_html_without_saving(client_as):
    c = client_as("editor")
    admin = models.get_user_by_email("admin@example.test")
    program = _seed_program(admin.id)

    page = c.get(f"/admin/posts/new?program_id={program.id}")
    token = _csrf_token_from(page.text)
    malicious = 'Hi <script>alert(1)</script> <img src=x onerror="alert(2)">'
    response = c.post(
        "/admin/posts/new",
        data={"program_id": str(program.id), "title": "Draft", "body": malicious,
              "topic": "general", "action": "preview", "csrf_token": token},
    )
    assert response.status_code == 200
    assert "<script>" not in response.text
    assert 'onerror="' not in response.text  # live attribute, not Jinja's escaped &#34;
    # Nothing was saved by the preview action.
    assert models.list_posts_by_program(program.id) == []


def test_slug_regenerates_while_draft_then_freezes_once_not_draft(client_as):
    c = client_as("editor")
    admin = models.get_user_by_email("admin@example.test")
    program = _seed_program(admin.id)
    _create_post(c, program.id, "First Title")
    post = models.list_posts_by_program(program.id)[0]
    assert post.slug == "first-title"

    edit_page = c.get(f"/admin/posts/{post.id}/edit")
    token = _csrf_token_from(edit_page.text)
    c.post(f"/admin/posts/{post.id}/edit",
           data={"title": "Renamed Title", "body": "x", "topic": "housing",
                 "action": "save", "csrf_token": token})
    assert models.get_post_by_id(post.id).slug == "renamed-title"

    # No submit/publish route exists yet (T04); exercise the model's freeze
    # rule directly, same seam the spec calls out for the state machine.
    from app import db
    conn = db.get_connection()
    conn.execute("UPDATE posts SET status = 'pending' WHERE id = ?", (post.id,))
    conn.commit()
    conn.close()

    models.update_post(post.id, title="Title After Pending", body="x", topic="housing")
    after = models.get_post_by_id(post.id)
    assert after.title == "Title After Pending"
    assert after.slug == "renamed-title"  # frozen


def test_ambassador_blocked_from_another_users_post(client_as):
    admin = models.get_user_by_email("admin@example.test")
    program = _seed_program(admin.id)

    owner = client_as("editor")
    _create_post(owner, program.id, "Owner's Post")
    post = models.list_posts_by_program(program.id)[0]

    other = models.create_user(
        email="other-editor@example.test", password="test-other-pw",
        role="editor", display_name="Other Ambassador",
    )
    intruder = client_as("editor")
    # Force the second client to actually be logged in as `other`, not the
    # shared demo editor, by logging out and back in as the new account.
    login_page = intruder.get("/login")
    token = _csrf_token_from(login_page.text)
    intruder.post("/login", data={"email": other.email, "password": "test-other-pw",
                                   "csrf_token": token})

    assert intruder.get(f"/admin/posts/{post.id}/edit").status_code == 403
    assert intruder.get(f"/admin/posts/{post.id}/delete").status_code == 403

    token = _admin_csrf(owner)  # any valid session token; route 403s before using it
    response = intruder.post(f"/admin/posts/{post.id}/edit",
                              data={"title": "Hijacked", "body": "x", "topic": "other",
                                    "action": "save", "csrf_token": token})
    assert response.status_code == 403
    assert models.get_post_by_id(post.id).title == "Owner's Post"


def test_admin_can_edit_and_delete_any_draft_post(client_as):
    admin_c = client_as("admin")
    admin = models.get_user_by_email("admin@example.test")
    program = _seed_program(admin.id)

    editor_c = client_as("editor")
    _create_post(editor_c, program.id, "Ambassador Draft")
    post = models.list_posts_by_program(program.id)[0]

    edit_page = admin_c.get(f"/admin/posts/{post.id}/edit")
    assert edit_page.status_code == 200
    token = _csrf_token_from(edit_page.text)
    admin_c.post(f"/admin/posts/{post.id}/edit",
                 data={"title": "Staff Edited This", "body": "x", "topic": "academics",
                       "action": "save", "csrf_token": token})
    assert models.get_post_by_id(post.id).title == "Staff Edited This"

    confirm = admin_c.get(f"/admin/posts/{post.id}/delete")
    token = _csrf_token_from(confirm.text)
    admin_c.post(f"/admin/posts/{post.id}/delete", data={"csrf_token": token})
    assert models.get_post_by_id(post.id) is None


def test_anonymous_redirected_to_login_for_post_routes(client):
    admin = models.get_user_by_email("admin@example.test")
    program = _seed_program(admin.id)
    response = client.get(f"/admin/posts?program_id={program.id}", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_create_post_requires_a_program_level_page(client_as):
    c = client_as("editor")
    admin = models.get_user_by_email("admin@example.test")
    home = models.ensure_home_page()
    continent = models.create_page(home.id, "Africa", "", False, admin.id)

    # Rejected up front, before the user fills out a form that can never save
    # (models.create_post enforces the same rule as the model layer's own
    # guarantee, independent of this route-level check).
    assert c.get(f"/admin/posts/new?program_id={continent.id}").status_code == 400

    token = _admin_csrf(c)
    response = c.post(
        "/admin/posts/new",
        data={"program_id": str(continent.id), "title": "Not Under A Program",
              "body": "x", "topic": "housing", "action": "save", "csrf_token": token},
    )
    assert response.status_code == 400
    assert models.list_posts_by_program(continent.id) == []


def test_seed_demo_seeds_posts_across_topics(client):
    """Status coverage (draft/pending/published) is T04's acceptance
    criterion — see tests/test_t04.py; this just covers Topic variety.

    T11 follow-up: each Program now gets 3 posts (one from the Ambassador
    Demo account, two from other fictional Ambassadors) across 3 Topics,
    not just one post authored solely by the editor."""
    seed_demo = _load_seed_demo()

    admin = models.get_user_by_email("admin@example.test")
    editor = models.get_user_by_email("editor@example.test")
    programs = seed_demo._seed_pages(admin.id)
    seed_demo._seed_posts(programs, editor.id)

    all_posts = [p for program in programs for p in models.list_posts_by_program(program.id)]
    assert len(all_posts) == len(programs) * 3
    assert len({p.topic for p in all_posts}) > 1
    editor_posts = [p for p in all_posts if p.author_id == editor.id]
    assert len(editor_posts) == len(programs)  # the seeded editor account's own anchor post
    assert any(p.author_id != editor.id for p in all_posts)  # plus other fictional Ambassadors
