"""Shared test fixtures.

`client` gives you the app. `client_as(role)` gives you a client that is logged
in as a seeded user of that role — it works as soon as your login route exists,
so access-control tests stay one line:

    def test_editor_cannot_manage_users(client_as):
        assert client_as("editor").get("/admin/users").status_code in (302, 403)
"""
from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient

from app import settings
from app.main import create_app

# Matches scripts/seed_demo.py. Passwords come from the environment there; in
# tests they are fixed and meaningless.
DEMO_USERS = {
    "admin": {"email": "admin@example.test", "password": "test-admin-pw"},
    "editor": {"email": "editor@example.test", "password": "test-editor-pw"},
}
DEACTIVATED_USER = {"email": "deactivated@example.test", "password": "test-deactivated-pw"}

_CSRF_RE = re.compile(r'name="csrf_token" value="([^"]+)"')


def _csrf_token_from(html: str) -> str:
    match = _CSRF_RE.search(html)
    return match.group(1) if match else ""


@pytest.fixture
def seeded_db(tmp_path, monkeypatch) -> None:
    """Point the app at a fresh per-test SQLite file, seeded with DEMO_USERS
    plus one deactivated user — independent of the developer's own .env."""
    monkeypatch.setattr(settings, "DATABASE_PATH", tmp_path / "test.db")

    from app import db, models

    db.init_db()
    models.create_user(email=DEMO_USERS["admin"]["email"],
                        password=DEMO_USERS["admin"]["password"],
                        role="admin", display_name="Staff Demo")
    models.create_user(email=DEMO_USERS["editor"]["email"],
                        password=DEMO_USERS["editor"]["password"],
                        role="editor", display_name="Ambassador Demo")
    models.create_user(email=DEACTIVATED_USER["email"],
                        password=DEACTIVATED_USER["password"],
                        role="editor", display_name="Deactivated Demo", active=False)


@pytest.fixture
def client(seeded_db) -> TestClient:
    return TestClient(create_app())


@pytest.fixture
def client_as(seeded_db):
    """Return a factory: client_as("editor") -> a logged-in TestClient."""

    def _login(role: str) -> TestClient:
        user = DEMO_USERS[role]
        c = TestClient(create_app())
        login_page = c.get("/login")
        if login_page.status_code == 404:
            pytest.skip("No /login route yet — build the login ticket first.")
        csrf_token = _csrf_token_from(login_page.text)
        response = c.post("/login", data={"email": user["email"],
                                          "password": user["password"],
                                          "csrf_token": csrf_token},
                          follow_redirects=False)
        assert response.status_code in (200, 302, 303), (
            f"Login as {role} failed with {response.status_code}")
        return c

    return _login
