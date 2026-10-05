#!/usr/bin/env python3
"""Create demo data so a grader (and you) can use the CMS immediately.

    uv run python scripts/seed_demo.py

T00 has nothing to seed. As you build content types, extend this so it creates:
  - one admin and one editor (passwords read from .env, never hard-coded)
  - a few posts and pages, at least one draft and one published

The rubric expects this to run clean on a fresh clone with .env.example values
(item E4), because the database itself is never committed.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import db, models  # noqa: E402


def main() -> int:
    admin_pw = os.environ.get("CMS_ADMIN_PASSWORD")
    editor_pw = os.environ.get("CMS_EDITOR_PASSWORD")
    deactivated_pw = os.environ.get("CMS_DEACTIVATED_PASSWORD", "change-me-deactivated")
    if not admin_pw or not editor_pw:
        print("Set CMS_ADMIN_PASSWORD and CMS_EDITOR_PASSWORD in .env "
              "(copy .env.example).")
        return 1

    db.init_db()
    for email, pw, role, name, active in [
        ("admin@example.test", admin_pw, "admin", "Staff Demo", True),
        ("editor@example.test", editor_pw, "editor", "Ambassador Demo", True),
        ("deactivated@example.test", deactivated_pw, "editor", "Deactivated Demo", False),
    ]:
        if models.get_user_by_email(email) is None:
            models.create_user(email=email, password=pw, role=role,
                                display_name=name, active=active)
    print("Seeded admin, editor, and deactivated demo users.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
