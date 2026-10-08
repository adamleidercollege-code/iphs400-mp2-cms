"""Plain SQLite connection handling (no ORM, per ADR-002)."""
from __future__ import annotations

import sqlite3

from app import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'editor')),
    display_name TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- An uploaded image (#15): a safe generated filename, never the one the
-- browser sent, plus the alt text required before anything can reference it.
-- post_id is set only for an image uploaded inline into a Post's body (never
-- for a cover, which is always a freshly-uploaded file the cover route
-- attaches directly) — it's what lets a Post's body safely reference
-- "media/<id>" as free text: app.services.post_view.owned_media_ids only
-- resolves/copies an id this Post itself uploaded, so hand-typing another
-- Post's (or a draft's) id can never pull that file into a published page.
CREATE TABLE IF NOT EXISTS media (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL UNIQUE,
    content_type TEXT NOT NULL,
    size INTEGER NOT NULL,
    alt_text TEXT NOT NULL,
    uploaded_by INTEGER,
    post_id INTEGER REFERENCES posts(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS pages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_id INTEGER REFERENCES pages(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    slug TEXT NOT NULL,
    body TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL CHECK (status IN ('draft', 'published')) DEFAULT 'draft',
    show_in_footer INTEGER NOT NULL DEFAULT 0,
    author_id INTEGER,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    published_at TEXT,
    cover_media_id INTEGER REFERENCES media(id)
);

-- At most one root (parent_id IS NULL) Page — the single Home — ever exists.
CREATE UNIQUE INDEX IF NOT EXISTS idx_pages_single_home ON pages((1)) WHERE parent_id IS NULL;

CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    program_id INTEGER NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    slug TEXT NOT NULL,
    body TEXT NOT NULL DEFAULT '',
    topic TEXT NOT NULL CHECK (topic IN
        ('general', 'housing', 'meals', 'social-life', 'academics', 'other'))
        DEFAULT 'general',
    status TEXT NOT NULL CHECK (status IN ('draft', 'pending', 'published')) DEFAULT 'draft',
    author_id INTEGER,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    published_at TEXT,
    cover_media_id INTEGER REFERENCES media(id)
);

-- A Staff-curated label (CONTEXT.md: Tag), independent of Topic.
CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- A Post's multi-select Tags (Topic stays its own single column on posts).
CREATE TABLE IF NOT EXISTS post_tags (
    post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (post_id, tag_id)
);
"""


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    conn = get_connection()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()
