"""Plain SQLite access (no ORM, per ADR-002). User and Page reads and writes."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from app import db
from app.services import passwords, slugs


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


@dataclass(frozen=True)
class Page:
    id: int
    parent_id: int | None
    title: str
    slug: str
    body: str
    status: str
    show_in_footer: bool
    author_id: int | None
    created_at: str
    updated_at: str
    published_at: str | None


def _row_to_page(row: sqlite3.Row) -> Page:
    return Page(
        id=row["id"],
        parent_id=row["parent_id"],
        title=row["title"],
        slug=row["slug"],
        body=row["body"],
        status=row["status"],
        show_in_footer=bool(row["show_in_footer"]),
        author_id=row["author_id"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        published_at=row["published_at"],
    )


def get_page_by_id(page_id: int) -> Page | None:
    conn = db.get_connection()
    try:
        row = conn.execute("SELECT * FROM pages WHERE id = ?", (page_id,)).fetchone()
        return _row_to_page(row) if row else None
    finally:
        conn.close()


def get_home_page() -> Page | None:
    conn = db.get_connection()
    try:
        row = conn.execute("SELECT * FROM pages WHERE parent_id IS NULL").fetchone()
        return _row_to_page(row) if row else None
    finally:
        conn.close()


def ensure_home_page() -> Page:
    """Create the single root Page (no parent) if it doesn't exist yet.

    Guarded by a partial unique index (db.py: idx_pages_single_home) against
    two concurrent first-requests both inserting a Home row; the loser's
    insert raises IntegrityError here, and we just re-read the winner's row.
    """
    home = get_home_page()
    if home is not None:
        return home
    conn = db.get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO pages (parent_id, title, slug, body, status, show_in_footer, "
            "author_id, published_at) "
            "VALUES (NULL, 'Home', '', '', 'published', 0, NULL, "
            "strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))"
        )
        conn.commit()
        return get_page_by_id(cur.lastrowid)
    except sqlite3.IntegrityError:
        return get_home_page()
    finally:
        conn.close()


def list_children(parent_id: int) -> list[Page]:
    conn = db.get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM pages WHERE parent_id = ? ORDER BY title", (parent_id,)
        ).fetchall()
        return [_row_to_page(r) for r in rows]
    finally:
        conn.close()


def list_published_children(parent_id: int) -> list[Page]:
    """Non-footer, published children — the generic "body lists its children" rule."""
    conn = db.get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM pages WHERE parent_id = ? AND status = 'published' "
            "AND show_in_footer = 0 ORDER BY title",
            (parent_id,),
        ).fetchall()
        return [_row_to_page(r) for r in rows]
    finally:
        conn.close()


def list_footer_pages() -> list[Page]:
    conn = db.get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM pages WHERE status = 'published' AND show_in_footer = 1 "
            "ORDER BY title"
        ).fetchall()
        return [_row_to_page(r) for r in rows]
    finally:
        conn.close()


def get_child_by_slug(parent_id: int, slug: str) -> Page | None:
    conn = db.get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM pages WHERE parent_id = ? AND slug = ?", (parent_id, slug)
        ).fetchone()
        return _row_to_page(row) if row else None
    finally:
        conn.close()


def list_all_pages() -> list[Page]:
    conn = db.get_connection()
    try:
        rows = conn.execute("SELECT * FROM pages").fetchall()
        return [_row_to_page(r) for r in rows]
    finally:
        conn.close()


def list_ancestors(page: Page) -> list[Page]:
    """Home first, down to (but not including) `page` itself."""
    chain: list[Page] = []
    current = page
    while current.parent_id is not None:
        parent = get_page_by_id(current.parent_id)
        chain.append(parent)
        current = parent
    chain.reverse()
    return chain


def create_page(
    parent_id: int, title: str, body: str, show_in_footer: bool, author_id: int
) -> Page:
    if get_page_by_id(parent_id) is None:
        raise ValueError(f"parent page {parent_id} does not exist")
    sibling_slugs = {c.slug for c in list_children(parent_id)}
    slug = slugs.dedupe(slugs.slugify(title), sibling_slugs)
    conn = db.get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO pages (parent_id, title, slug, body, status, show_in_footer, "
            "author_id) VALUES (?, ?, ?, ?, 'draft', ?, ?)",
            (parent_id, title, slug, body, int(show_in_footer), author_id),
        )
        conn.commit()
        return get_page_by_id(cur.lastrowid)
    finally:
        conn.close()


def update_page(page_id: int, title: str, body: str, show_in_footer: bool) -> Page:
    page = get_page_by_id(page_id)
    if page is None:
        raise ValueError(f"page {page_id} does not exist")
    if page.status == "draft":
        sibling_slugs = {
            c.slug for c in list_children(page.parent_id) if c.id != page.id
        }
        slug = slugs.dedupe(slugs.slugify(title), sibling_slugs)
    else:
        slug = page.slug  # frozen the moment status leaves draft
    conn = db.get_connection()
    try:
        conn.execute(
            "UPDATE pages SET title = ?, slug = ?, body = ?, show_in_footer = ?, "
            "updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = ?",
            (title, slug, body, int(show_in_footer), page_id),
        )
        conn.commit()
        return get_page_by_id(page_id)
    finally:
        conn.close()


def publish_page(page_id: int) -> Page:
    conn = db.get_connection()
    try:
        conn.execute(
            "UPDATE pages SET status = 'published', "
            "published_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now'), "
            "updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = ?",
            (page_id,),
        )
        conn.commit()
        return get_page_by_id(page_id)
    finally:
        conn.close()


def delete_page(page_id: int) -> None:
    page = get_page_by_id(page_id)
    if page is not None and page.parent_id is None:
        raise ValueError("cannot delete the Home page")
    conn = db.get_connection()
    try:
        conn.execute("DELETE FROM pages WHERE id = ?", (page_id,))
        conn.commit()
    finally:
        conn.close()
