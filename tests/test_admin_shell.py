"""Issue #13: the admin console's shared stylesheet, sidebar, and
post-save flash messages (app/services/console_shell.py)."""
from __future__ import annotations

import re
from urllib.parse import urljoin

from app import models


def _csrf_token_from(html: str) -> str:
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    return match.group(1) if match else ""


def _seed_program(author_id: int) -> models.Page:
    home = models.ensure_home_page()
    continent = models.create_page(home.id, "Asia", "", False, author_id)
    country = models.create_page(continent.id, "Japan", "", False, author_id)
    return models.create_page(country.id, "Kyoto Exchange", "", False, author_id)


def test_admin_stylesheet_is_served_at_a_fixed_url(client):
    response = client.get("/style.css")
    assert response.status_code == 200
    assert "text/css" in response.headers["content-type"]
    assert ".console-sidebar" in response.text


def test_nested_admin_pages_link_a_correctly_relative_stylesheet(client_as):
    """A literal root-absolute href would fail check_submission.py's scan of
    every tracked template, so every admin page computes its own "../" depth
    back to the one /style.css route instead (console_shell.css_path_for)."""
    admin = client_as("admin")
    program = _seed_program(models.get_user_by_email("admin@example.test").id)
    post = models.create_post(
        program_id=program.id, title="A post", body="Body.", topic="general",
        author_id=models.get_user_by_email("admin@example.test").id,
    )
    for path in ["/login", "/admin", "/admin/dashboard", "/admin/accounts",
                 f"/admin/posts/{post.id}/edit"]:
        response = admin.get(path)
        href = re.search(r'<link rel="stylesheet" href="([^"]+)"', response.text).group(1)
        assert not href.startswith("/"), f"{path}: root-absolute href {href!r}"
        resolved = urljoin(f"http://testserver{path}", href)
        assert resolved == "http://testserver/style.css", (path, href, resolved)


def test_stylesheet_resolved_from_a_nested_admin_page_returns_200(client_as):
    """The literal scenario the acceptance criteria asks for: follow a deeply
    nested admin page's own stylesheet link, not just assert /style.css
    works in isolation."""
    admin = client_as("admin")
    admin_id = models.get_user_by_email("admin@example.test").id
    program = _seed_program(admin_id)
    post = models.create_post(
        program_id=program.id, title="A post", body="Body.", topic="general",
        author_id=admin_id,
    )
    nested_path = f"/admin/posts/{post.id}/edit"
    response = admin.get(nested_path)
    href = re.search(r'<link rel="stylesheet" href="([^"]+)"', response.text).group(1)
    resolved = urljoin(f"http://testserver{nested_path}", href)

    stylesheet = admin.get(urljoin(nested_path, href))
    assert stylesheet.status_code == 200, (nested_path, href, resolved)
    assert "text/css" in stylesheet.headers["content-type"]


def test_accounts_posts_and_pages_screens_have_the_persistent_sidebar(client_as):
    admin = client_as("admin")
    program = _seed_program(models.get_user_by_email("admin@example.test").id)
    post = models.create_post(
        program_id=program.id, title="A post", body="Body.", topic="general",
        author_id=models.get_user_by_email("admin@example.test").id,
    )
    for path in ["/admin/accounts", "/admin/pages", f"/admin/posts/{post.id}/edit"]:
        response = admin.get(path)
        assert 'class="console-sidebar"' in response.text, path
        assert ">Dashboard<" in response.text, path


def test_ambassador_sidebar_only_lists_my_posts(client_as):
    editor = client_as("editor")
    response = editor.get("/admin")
    assert 'class="console-sidebar"' in response.text
    assert ">My posts<" in response.text
    assert ">Dashboard<" not in response.text


def test_creating_an_account_shows_a_success_flash(client_as):
    admin = client_as("admin")
    new_form = admin.get("/admin/accounts/new")
    token = _csrf_token_from(new_form.text)
    response = admin.post(
        "/admin/accounts/new",
        data={"email": "flash-test@example.test", "display_name": "Flash Test",
              "password": "a-long-enough-password", "role": "editor",
              "csrf_token": token},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "Account created." in response.text
    assert 'class="flash"' in response.text


def test_delete_confirmations_use_the_destructive_button_style(client_as):
    admin = client_as("admin")
    admin_user = models.get_user_by_email("admin@example.test")
    program = _seed_program(admin_user.id)
    post = models.create_post(
        program_id=program.id, title="A post", body="Body.", topic="general",
        author_id=admin_user.id,
    )

    post_delete = admin.get(f"/admin/posts/{post.id}/delete")
    assert 'class="btn-danger"' in post_delete.text

    page_delete = admin.get(f"/admin/pages/{program.id}/delete")
    assert 'class="btn-danger"' in page_delete.text
