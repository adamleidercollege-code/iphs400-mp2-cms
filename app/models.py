"""Plain SQLite access (no ORM, per ADR-002). User and Page reads and writes."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from app import db
from app.services import deactivation, passwords, slugs


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


def list_users() -> list[User]:
    conn = db.get_connection()
    try:
        rows = conn.execute("SELECT * FROM users ORDER BY email").fetchall()
        return [_row_to_user(r) for r in rows]
    finally:
        conn.close()


def set_user_role(user_id: int, role: str) -> User:
    """Change an existing user's role (Staff <-> Ambassador). This is a
    plain role reassignment, not a deactivation — it never triggers the
    deactivation cascade, since the user stays active throughout.
    """
    if role not in ("admin", "editor"):
        raise ValueError(f"invalid role: {role!r}")
    if get_user_by_id(user_id) is None:
        raise ValueError(f"user {user_id} does not exist")
    conn = db.get_connection()
    try:
        conn.execute(
            "UPDATE users SET role = ?, "
            "updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = ?",
            (role, user_id),
        )
        conn.commit()
        return get_user_by_id(user_id)
    finally:
        conn.close()


def _set_user_active(user_id: int, active: bool) -> User:
    conn = db.get_connection()
    try:
        conn.execute(
            "UPDATE users SET active = ?, "
            "updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = ?",
            (int(active), user_id),
        )
        conn.commit()
        return get_user_by_id(user_id)
    finally:
        conn.close()


def deactivate_user(user_id: int) -> User:
    """Mark the user inactive, applying the role-specific cascade
    (app.services.deactivation): an Ambassador's draft Posts are deleted; a
    Staff member's drafts are left exactly as they are. Pending and
    published Posts are left untouched either way, byline intact.
    """
    user = get_user_by_id(user_id)
    if user is None:
        raise ValueError(f"user {user_id} does not exist")
    if deactivation.should_delete_drafts(user.role):
        for post in list_posts_by_author(user_id):
            if post.status == "draft":
                delete_post(post.id)
    return _set_user_active(user_id, False)


def reactivate_user(user_id: int) -> User:
    if get_user_by_id(user_id) is None:
        raise ValueError(f"user {user_id} does not exist")
    return _set_user_active(user_id, True)


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


TOPIC_CHOICES = [
    ("general", "General"),
    ("housing", "Housing"),
    ("meals", "Meals"),
    ("social-life", "Social Life"),
    ("academics", "Academics"),
    ("other", "Other"),
]
TOPIC_VALUES = {value for value, _label in TOPIC_CHOICES}


@dataclass(frozen=True)
class Post:
    id: int
    program_id: int
    title: str
    slug: str
    body: str
    topic: str
    status: str
    author_id: int | None
    created_at: str
    updated_at: str
    published_at: str | None


def _row_to_post(row: sqlite3.Row) -> Post:
    return Post(
        id=row["id"],
        program_id=row["program_id"],
        title=row["title"],
        slug=row["slug"],
        body=row["body"],
        topic=row["topic"],
        status=row["status"],
        author_id=row["author_id"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        published_at=row["published_at"],
    )


def get_post_by_id(post_id: int) -> Post | None:
    conn = db.get_connection()
    try:
        row = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
        return _row_to_post(row) if row else None
    finally:
        conn.close()


def list_posts_by_program(program_id: int) -> list[Post]:
    conn = db.get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM posts WHERE program_id = ? ORDER BY created_at DESC",
            (program_id,),
        ).fetchall()
        return [_row_to_post(r) for r in rows]
    finally:
        conn.close()


def list_published_posts_by_program(program_id: int) -> list[Post]:
    """Public-facing: only published Posts, most recent first. A draft or
    pending Post must never reach a public response (hard constraint)."""
    conn = db.get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM posts WHERE program_id = ? AND status = 'published' "
            "ORDER BY published_at DESC",
            (program_id,),
        ).fetchall()
        return [_row_to_post(r) for r in rows]
    finally:
        conn.close()


def list_recent_published_posts(limit: int) -> list[Post]:
    """Newest published Posts across the whole site — Home's latest-dispatches
    strip. Same published-only rule as every other public-facing query."""
    conn = db.get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM posts WHERE status = 'published' "
            "ORDER BY published_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [_row_to_post(r) for r in rows]
    finally:
        conn.close()


def list_published_posts_under(page_id: int, limit: int) -> list[Post]:
    """Newest published Posts written under any Program in `page_id`'s
    subtree — the "recent posts from this Continent/Country" strip. Returns
    nothing for a Program (use list_published_posts_by_program) or a leaf."""
    program_ids: list[int] = []
    frontier = list_published_children(page_id)
    while frontier:
        page = frontier.pop()
        if is_program_page(page):
            program_ids.append(page.id)
        else:
            frontier.extend(list_published_children(page.id))
    if not program_ids:
        return []
    placeholders = ",".join("?" for _ in program_ids)
    conn = db.get_connection()
    try:
        rows = conn.execute(
            f"SELECT * FROM posts WHERE status = 'published' "
            f"AND program_id IN ({placeholders}) "
            "ORDER BY published_at DESC LIMIT ?",
            (*program_ids, limit),
        ).fetchall()
        return [_row_to_post(r) for r in rows]
    finally:
        conn.close()


def backdate_post(post_id: int, timestamp: str) -> Post:
    """Move a Post's timestamps back in time. Only scripts/seed_demo.py uses
    this, so the demo catalog reads like posts written over a term rather
    than eighteen posts filed the same second."""
    conn = db.get_connection()
    try:
        conn.execute(
            "UPDATE posts SET created_at = ?, updated_at = ?, "
            "published_at = CASE WHEN published_at IS NULL THEN NULL ELSE ? END "
            "WHERE id = ?",
            (timestamp, timestamp, timestamp, post_id),
        )
        conn.commit()
        return get_post_by_id(post_id)
    finally:
        conn.close()


def list_all_posts() -> list[Post]:
    conn = db.get_connection()
    try:
        rows = conn.execute("SELECT * FROM posts ORDER BY created_at DESC").fetchall()
        return [_row_to_post(r) for r in rows]
    finally:
        conn.close()


def list_posts_by_author(author_id: int) -> list[Post]:
    conn = db.get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM posts WHERE author_id = ?", (author_id,)
        ).fetchall()
        return [_row_to_post(r) for r in rows]
    finally:
        conn.close()


def get_published_post_by_slug(program_id: int, slug: str) -> Post | None:
    conn = db.get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM posts WHERE program_id = ? AND slug = ? AND status = 'published'",
            (program_id, slug),
        ).fetchone()
        return _row_to_post(row) if row else None
    finally:
        conn.close()


def group_posts_by_topic(posts: list[Post]) -> list[tuple[str, str, list[Post]]]:
    """Posts in Topic order (CONTEXT.md: General first, then each Hot Topic),
    skipping any Topic with nothing to show."""
    buckets: dict[str, list[Post]] = {value: [] for value, _label in TOPIC_CHOICES}
    for post in posts:
        buckets[post.topic].append(post)
    return [
        (value, label, buckets[value])
        for value, label in TOPIC_CHOICES
        if buckets[value]
    ]


def is_program_page(page: Page) -> bool:
    """A Program is the Page three levels below Home (Home -> Continent ->
    Country -> Program), per CONTEXT.md and the spec's Post.program_id field."""
    return len(list_ancestors(page)) == 3


def is_continent_page(page: Page) -> bool:
    """A Continent is the Page one level below Home, minus the standalone
    Pages that also sit at that depth (About CGE, Contact Us) — the same
    show_in_footer split list_published_children already uses to keep
    standalone Pages out of the Continent list that drives nav and
    region_index. Without this, a Continent flagged "show in footer" would
    satisfy is_continent_page and is_standalone_page at once (see
    is_standalone_page)."""
    return len(list_ancestors(page)) == 1 and not page.show_in_footer


def is_country_page(page: Page) -> bool:
    """A Country is the Page two levels below Home — its children are Programs."""
    return len(list_ancestors(page)) == 2


def is_standalone_page(page: Page) -> bool:
    """A standalone Page sits directly under Home and is reachable only from
    the footer (CONTEXT.md: About CGE, Contact Us). It holds prose rather
    than a branch of the Continent tree, so it gets its own public layout."""
    return len(list_ancestors(page)) == 1 and page.show_in_footer


def nav_root_id(page: Page, home: Page) -> int:
    """Which top-nav item (Home or a Continent) `page` lives under, so the
    public header can highlight the active one."""
    if page.id == home.id:
        return home.id
    ancestors = list_ancestors(page)
    if len(ancestors) <= 1:
        return page.id
    return ancestors[1].id


def create_post(program_id: int, title: str, body: str, topic: str, author_id: int) -> Post:
    program = get_page_by_id(program_id)
    if program is None:
        raise ValueError(f"program page {program_id} does not exist")
    if not is_program_page(program):
        raise ValueError(f"page {program_id} is not a Program-level page")
    if topic not in TOPIC_VALUES:
        raise ValueError(f"invalid topic: {topic!r}")
    sibling_slugs = {p.slug for p in list_posts_by_program(program_id)}
    slug = slugs.dedupe(slugs.slugify(title), sibling_slugs)
    conn = db.get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO posts (program_id, title, slug, body, topic, author_id) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (program_id, title, slug, body, topic, author_id),
        )
        conn.commit()
        return get_post_by_id(cur.lastrowid)
    finally:
        conn.close()


def update_post(post_id: int, title: str, body: str, topic: str) -> Post:
    post = get_post_by_id(post_id)
    if post is None:
        raise ValueError(f"post {post_id} does not exist")
    if topic not in TOPIC_VALUES:
        raise ValueError(f"invalid topic: {topic!r}")
    if post.status == "draft":
        sibling_slugs = {
            p.slug for p in list_posts_by_program(post.program_id) if p.id != post.id
        }
        slug = slugs.dedupe(slugs.slugify(title), sibling_slugs)
    else:
        slug = post.slug  # frozen the moment status leaves draft
    conn = db.get_connection()
    try:
        conn.execute(
            "UPDATE posts SET title = ?, slug = ?, body = ?, topic = ?, "
            "updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = ?",
            (title, slug, body, topic, post_id),
        )
        conn.commit()
        return get_post_by_id(post_id)
    finally:
        conn.close()


class StatusConflict(Exception):
    """Raised by set_post_status when the Post's status no longer matches
    `from_status` — another request changed it between the caller's read and
    this write, e.g. one admin bounced a pending Post the instant another
    admin published it. The caller re-reads and re-authorizes rather than
    overwriting a decision it never actually validated."""


def set_post_status(post_id: int, from_status: str, to_status: str) -> Post:
    """Apply a review-gate transition (app.services.review_gate.transition
    decides `to_status`; this is the one place that writes it), guarded by
    `WHERE status = from_status` so a stale read can never clobber a status
    change made in between. published_at is set on entry to 'published' and
    cleared on any exit from it, so it never lingers on a Post that isn't
    currently live.
    """
    conn = db.get_connection()
    try:
        published_at_sql = (
            "published_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now'), "
            if to_status == "published" else "published_at = NULL, "
        )
        cur = conn.execute(
            "UPDATE posts SET status = ?, " + published_at_sql +
            "updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') "
            "WHERE id = ? AND status = ?",
            (to_status, post_id, from_status),
        )
        conn.commit()
        if cur.rowcount == 0:
            raise StatusConflict(
                f"post {post_id} is no longer {from_status!r}; refresh and retry"
            )
        return get_post_by_id(post_id)
    finally:
        conn.close()


def delete_post(post_id: int) -> None:
    conn = db.get_connection()
    try:
        conn.execute("DELETE FROM posts WHERE id = ?", (post_id,))
        conn.commit()
    finally:
        conn.close()
