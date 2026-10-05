"""CSRF token generation and comparison — pure, no FastAPI or SQLite dependency."""
from __future__ import annotations

import secrets


def generate_token() -> str:
    return secrets.token_urlsafe(32)


def tokens_match(session_token: str | None, submitted_token: str | None) -> bool:
    if not session_token or not submitted_token:
        return False
    return secrets.compare_digest(session_token, submitted_token)
