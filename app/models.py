"""Plain SQLite access (no ORM, per ADR-002). User reads and writes."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from app import db
from app.services import passwords


ROLE_LABELS = {"admin": "Staff", "editor": "Ambassador"}


@dataclass(frozen=True)
class User:
    id: int
    email: str
    password_hash: str
    role: str
    display_name: str
    active: bool
    created_at: str
    updated_at: str

    @property
    def role_label(self) -> str:
        """The UI-facing role name (CONTEXT.md: Staff/Ambassador, never admin/editor)."""
        return ROLE_LABELS[self.role]


def _row_to_user(row: sqlite3.Row) -> User:
    return User(
        id=row["id"],
        email=row["email"],
        password_hash=row["password_hash"],
        role=row["role"],
        display_name=row["display_name"],
        active=bool(row["active"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def create_user(
    email: str, password: str, role: str, display_name: str, active: bool = True
) -> User:
    conn = db.get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO users (email, password_hash, role, display_name, active) "
            "VALUES (?, ?, ?, ?, ?)",
            (email, passwords.hash_password(password), role, display_name, int(active)),
        )
        conn.commit()
        return get_user_by_id(cur.lastrowid)
    finally:
        conn.close()


def get_user_by_id(user_id: int) -> User | None:
    conn = db.get_connection()
    try:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return _row_to_user(row) if row else None
    finally:
        conn.close()


def get_user_by_email(email: str) -> User | None:
    conn = db.get_connection()
    try:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        return _row_to_user(row) if row else None
    finally:
        conn.close()
