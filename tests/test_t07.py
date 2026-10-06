"""T07: Staff console — dashboard, content list, pending queue, page
hierarchy, metrics."""
from __future__ import annotations

from app import models


def _seed_program(author_id: int) -> models.Page:
    home = models.ensure_home_page()
    continent = models.create_page(home.id, "Asia", "", False, author_id)
    country = models.create_page(continent.id, "Japan", "", False, author_id)
    return models.create_page(country.id, "Kyoto Exchange", "", False, author_id)


# --- Landing screen (GET /admin) --------------------------------------------


def test_staff_landing_is_a_live_preview_of_the_published_site(client_as):
    admin = models.get_user_by_email("admin@example.test")
    program = _seed_program(admin.id)
    models.publish_page(program.parent_id)
    models.publish_page(models.get_page_by_id(program.parent_id).parent_id)

    response = client_as("admin").get("/admin")
    assert response.status_code == 200
    assert "staff demo" in response.text.lower()
    assert "live preview" in response.text.lower()
    assert "Asia" in response.text


# --- Dashboard ---------------------------------------------------------------


def test_dashboard_shows_post_and_page_and_account_counts(client_as):
    admin = models.get_user_by_email("admin@example.test")
    program = _seed_program(admin.id)
    draft = models.create_post(program.id, "Draft Post", "body", "housing", admin.id)
    pending = models.create_post(program.id, "Pending Post", "body", "meals", admin.id)
    models.set_post_status(pending.id, from_status="draft", to_status="pending")

    response = client_as("admin").get("/admin/dashboard")
    assert response.status_code == 200
    assert "draft: 1" in response.text.lower()
    assert "pending: 1" in response.text.lower()
    assert "published: 0" in response.text.lower()
    assert "2 active account" in response.text.lower()
    assert draft.id and pending.id  # posts were created under the seeded program


def test_dashboard_counts_pages_by_level(client_as):
    admin = models.get_user_by_email("admin@example.test")
    _seed_program(admin.id)

    response = client_as("admin").get("/admin/dashboard")
    assert response.status_code == 200
    # Home (level 0), Asia (level 1), Japan (level 2), Kyoto Exchange (level 3).
    assert "home: 1" in response.text.lower()
    assert "level 1: 1" in response.text.lower()
    assert "level 2: 1" in response.text.lower()
    assert "level 3: 1" in response.text.lower()


# --- Content list -------------------------------------------------------------


def test_content_list_shows_posts_and_pages_together(client_as):
    admin = models.get_user_by_email("admin@example.test")
    program = _seed_program(admin.id)
    models.create_post(program.id, "A Draft Post", "body", "housing", admin.id)

    response = client_as("admin").get("/admin/content")
    assert response.status_code == 200
    assert "A Draft Post" in response.text
    assert "Kyoto Exchange" in response.text


def test_content_list_filters_by_status_and_type(client_as):
    admin = models.get_user_by_email("admin@example.test")
    program = _seed_program(admin.id)
    draft = models.create_post(program.id, "Still A Draft", "body", "housing", admin.id)
    published = models.create_post(program.id, "Now Published", "body", "meals", admin.id)
    models.set_post_status(published.id, from_status="draft", to_status="pending")
    models.set_post_status(published.id, from_status="pending", to_status="published")

    response = client_as("admin").get("/admin/content?status=draft&kind=post")
    assert response.status_code == 200
    assert "Still A Draft" in response.text
    assert "Now Published" not in response.text
    assert "Kyoto Exchange" not in response.text  # a Page, filtered out by kind=post


# --- Pending queue -------------------------------------------------------------


def test_pending_queue_lists_pending_posts_with_author_and_edit_link(client_as):
    admin = models.get_user_by_email("admin@example.test")
    editor = models.get_user_by_email("editor@example.test")
    program = _seed_program(admin.id)
    pending = models.create_post(
        program.id, "Waiting For Review", "body", "housing", editor.id
    )
    models.set_post_status(pending.id, from_status="draft", to_status="pending")
    draft = models.create_post(program.id, "Still Drafting", "body", "meals", editor.id)

    response = client_as("admin").get("/admin/pending")
    assert response.status_code == 200
    assert "Waiting For Review" in response.text
    assert "Ambassador Demo" in response.text
    assert f"/admin/posts/{pending.id}/edit" in response.text
    assert "Still Drafting" not in response.text
    assert draft.status == "draft"


# --- Metrics -------------------------------------------------------------------


def test_metrics_shows_posts_per_program_including_a_zero(client_as):
    admin = models.get_user_by_email("admin@example.test")
    home = models.ensure_home_page()
    continent = models.create_page(home.id, "Africa", "", False, admin.id)
    country = models.create_page(continent.id, "Kenya", "", False, admin.id)
    empty_program = models.create_page(country.id, "Nairobi Fieldwork", "", False, admin.id)
    busy_program = models.create_page(country.id, "Cape Town Semester", "", False, admin.id)
    models.create_post(busy_program.id, "One Post", "body", "housing", admin.id)

    response = client_as("admin").get("/admin/metrics")
    assert response.status_code == 200
    assert "Nairobi Fieldwork: 0" in response.text
    assert "Cape Town Semester: 1" in response.text
    assert empty_program.status == "draft"


# --- Access control: an Ambassador is blocked from every route in this ticket --


def test_ambassador_is_blocked_from_every_console_route(client_as):
    editor_c = client_as("editor")
    assert editor_c.get("/admin/dashboard").status_code == 403
    assert editor_c.get("/admin/content").status_code == 403
    assert editor_c.get("/admin/pending").status_code == 403
    assert editor_c.get("/admin/metrics").status_code == 403
    assert editor_c.get("/admin/pages").status_code == 403


def test_anonymous_request_is_redirected_to_login_for_every_console_route(client):
    for path in ("/admin/dashboard", "/admin/content", "/admin/pending", "/admin/metrics"):
        response = client.get(path, follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/login"
