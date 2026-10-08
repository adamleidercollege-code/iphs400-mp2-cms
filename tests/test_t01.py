"""T01: login, sessions, and role-gated access."""
from __future__ import annotations

from tests.conftest import DEACTIVATED_USER, DEMO_USERS, _csrf_token_from


def _login(client, email: str, password: str):
    page = client.get("/login")
    token = _csrf_token_from(page.text)
    return client.post(
        "/login",
        data={"email": email, "password": password, "csrf_token": token},
        follow_redirects=False,
    )


def test_admin_can_log_in_and_reach_admin(client):
    response = _login(client, DEMO_USERS["admin"]["email"], DEMO_USERS["admin"]["password"])
    assert response.status_code == 303
    assert response.headers["location"] == "/admin"
    followed = client.get("/admin")
    assert DEMO_USERS["admin"]["display_name"].lower() in followed.text.lower()


def test_editor_can_log_in_and_reach_admin(client):
    response = _login(client, DEMO_USERS["editor"]["email"], DEMO_USERS["editor"]["password"])
    assert response.status_code == 303
    followed = client.get("/admin")
    assert DEMO_USERS["editor"]["display_name"].lower() in followed.text.lower()


def test_wrong_password_is_refused_generically(client):
    response = _login(client, DEMO_USERS["admin"]["email"], "not-the-password")
    assert response.status_code == 401
    assert "incorrect email or password" in response.text.lower()


def test_unknown_email_gets_the_same_generic_message(client):
    response = _login(client, "nobody@example.test", "whatever")
    assert response.status_code == 401
    assert "incorrect email or password" in response.text.lower()


def test_deactivated_user_cannot_log_in(client):
    response = _login(client, DEACTIVATED_USER["email"], DEACTIVATED_USER["password"])
    assert response.status_code == 401
    assert "incorrect email or password" in response.text.lower()


def test_logout_ends_the_session(client_as):
    c = client_as("admin")
    page = c.get("/admin")
    assert DEMO_USERS["admin"]["display_name"].lower() in page.text.lower()

    token = _csrf_token_from(page.text)
    logout_response = c.post("/logout", data={"csrf_token": token},
                              follow_redirects=False)
    assert logout_response.status_code == 303

    after = c.get("/admin")
    assert DEMO_USERS["admin"]["display_name"].lower() not in after.text.lower()


def test_csrf_missing_token_rejected_on_logout(client_as):
    c = client_as("admin")
    response = c.post("/logout", data={}, follow_redirects=False)
    assert response.status_code == 403


def test_csrf_wrong_token_rejected_on_login(client):
    response = client.post(
        "/login",
        data={"email": DEMO_USERS["admin"]["email"],
              "password": DEMO_USERS["admin"]["password"],
              "csrf_token": "not-the-real-token"},
        follow_redirects=False,
    )
    assert response.status_code == 403


def test_stub_route_allows_admin(client_as):
    response = client_as("admin").get("/admin/_stub")
    assert response.status_code == 200


def test_stub_route_rejects_editor(client_as):
    response = client_as("editor").get("/admin/_stub")
    assert response.status_code == 403
    assert "this page is for cge staff only" in response.text.lower()
    assert 'href="/admin"' in response.text


def test_stub_route_redirects_anonymous(client):
    response = client.get("/admin/_stub", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"
