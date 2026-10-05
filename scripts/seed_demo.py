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

# Continent -> Country -> [Program, ...], per T02's seed requirement.
CONTINENTS = {
    "Asia": {
        "Japan": ["Kyoto Exchange"],
        "South Korea": ["Seoul Studies"],
    },
    "Africa": {
        "Kenya": ["Nairobi Fieldwork"],
        "South Africa": ["Cape Town Semester"],
    },
    "Europe": {
        "Spain": ["Madrid Language Immersion"],
        "France": ["Paris Arts & Culture"],
    },
}
STANDALONE_PAGES = ["About CGE", "Contact Us"]


def _placeholder_body(title: str) -> str:
    return (
        f"Placeholder copy for **{title}**. Replace this with real content "
        "once CGE has something to say here."
    )


def _seed_pages(admin_id: int) -> None:
    home = models.ensure_home_page()
    if models.list_children(home.id):
        print("Pages already seeded, leaving the tree as-is.")
        return

    def _add(parent_id: int, title: str, show_in_footer: bool = False) -> models.Page:
        page = models.create_page(
            parent_id=parent_id, title=title, body=_placeholder_body(title),
            show_in_footer=show_in_footer, author_id=admin_id,
        )
        return models.publish_page(page.id)

    for continent_title, countries in CONTINENTS.items():
        continent = _add(home.id, continent_title)
        for country_title, programs in countries.items():
            country = _add(continent.id, country_title)
            for program_title in programs:
                _add(country.id, program_title)

    for standalone_title in STANDALONE_PAGES:
        _add(home.id, standalone_title, show_in_footer=True)

    print("Seeded the Continent -> Country -> Program tree and standalone pages.")


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

    admin = models.get_user_by_email("admin@example.test")
    _seed_pages(admin.id)
    return 0


if __name__ == "__main__":
    sys.exit(main())
