"""T08: Ambassador console — My posts."""
from __future__ import annotations

from app import models


def _seed_program(author_id: int) -> models.Page:
    home = models.ensure_home_page()
    continent = models.create_page(home.id, "Asia", "", False, author_id)
    country = models.create_page(continent.id, "Japan", "", False, author_id)
    return models.create_page(country.id, "Kyoto Exchange", "", False, author_id)


def test_ambassador_landing_is_my_posts_grouped_by_status(client_as):
    admin = models.get_user_by_email("admin@example.test")
    editor = models.get_user_by_email("editor@example.test")
    program = _seed_program(admin.id)

    draft = models.create_post(program.id, "My Draft", "body", "housing", editor.id)
    pending = models.create_post(program.id, "My Pending", "body", "meals", editor.id)
    models.set_post_status(pending.id, from_status="draft", to_status="pending")
    published = models.create_post(program.id, "My Published", "body", "academics", editor.id)
    models.set_post_status(published.id, from_status="draft", to_status="pending")
    models.set_post_status(published.id, from_status="pending", to_status="published")

    response = client_as("editor").get("/admin")
    assert response.status_code == 200
    assert "My Draft" in response.text
    assert "My Pending" in response.text
    assert "My Published" in response.text
    assert draft.status == "draft"  # sanity: fixture statuses as expected


def test_my_posts_shows_only_the_logged_in_ambassadors_own_posts(client_as):
    admin = models.get_user_by_email("admin@example.test")
    editor = models.get_user_by_email("editor@example.test")
    program = _seed_program(admin.id)

    models.create_post(program.id, "Someone Elses Draft", "body", "housing", admin.id)
    models.create_post(program.id, "My Own Draft", "body", "housing", editor.id)

    response = client_as("editor").get("/admin")
    assert response.status_code == 200
    assert "My Own Draft" in response.text
    assert "Someone Elses Draft" not in response.text


def test_ambassador_sidebar_is_only_my_posts_and_logout(client_as):
    response = client_as("editor").get("/admin")
    assert response.status_code == 200
    assert "My posts" in response.text
    assert "Log out" in response.text
    for staff_label in ("Dashboard", "Content list", "Pending queue", "Accounts",
                        "Page hierarchy", "Metrics"):
        assert staff_label not in response.text


def test_ambassador_cannot_reach_any_staff_console_route(client_as):
    editor_c = client_as("editor")
    assert editor_c.get("/admin/dashboard").status_code == 403
    assert editor_c.get("/admin/content").status_code == 403
    assert editor_c.get("/admin/pending").status_code == 403
    assert editor_c.get("/admin/metrics").status_code == 403
    assert editor_c.get("/admin/pages").status_code == 403
    assert editor_c.get("/admin/accounts").status_code == 403


def test_staff_landing_still_shows_live_preview_not_my_posts(client_as):
    response = client_as("admin").get("/admin")
    assert response.status_code == 200
    assert "live preview" in response.text.lower()
    assert "My posts" not in response.text


def test_seed_demo_editor_has_a_post_in_every_status(seeded_db):
    from scripts import seed_demo

    admin = models.get_user_by_email("admin@example.test")
    editor = models.get_user_by_email("editor@example.test")
    programs = seed_demo._seed_pages(admin.id)
    seed_demo._seed_posts(programs, editor.id)

    editor_posts = models.list_posts_by_author(editor.id)
    statuses = {post.status for post in editor_posts}
    assert {"draft", "pending", "published"} <= statuses
