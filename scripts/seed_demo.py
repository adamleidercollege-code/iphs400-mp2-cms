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

# Cycled across the seeded Programs so posts land across different Topics
# (T03 acceptance: "a few draft Posts across different Topics").
POST_TOPICS = ["housing", "meals", "social-life", "academics", "other", "general"]

# Cycled too, so the review-gate workflow (ADR-004) is visible on a fresh
# clone (T04 acceptance): at least one Post in each status.
POST_STATUSES = ["draft", "pending", "published"]


def _placeholder_body(title: str) -> str:
    return (
        f"Placeholder copy for **{title}**. Replace this with real content "
        "once CGE has something to say here."
    )


def _seed_pages(admin_id: int) -> list[models.Page]:
    home = models.ensure_home_page()
    if models.list_children(home.id):
        print("Pages already seeded, leaving the tree as-is.")
        return [
            program
            for continent in models.list_children(home.id)
            for country in models.list_children(continent.id)
            for program in models.list_children(country.id)
        ]

    def _add(parent_id: int, title: str, show_in_footer: bool = False) -> models.Page:
        page = models.create_page(
            parent_id=parent_id, title=title, body=_placeholder_body(title),
            show_in_footer=show_in_footer, author_id=admin_id,
        )
        return models.publish_page(page.id)

    programs: list[models.Page] = []
    for continent_title, countries in CONTINENTS.items():
        continent = _add(home.id, continent_title)
        for country_title, program_titles in countries.items():
            country = _add(continent.id, country_title)
            for program_title in program_titles:
                programs.append(_add(country.id, program_title))

    for standalone_title in STANDALONE_PAGES:
        _add(home.id, standalone_title, show_in_footer=True)

    print("Seeded the Continent -> Country -> Program tree and standalone pages.")
    return programs


def _seed_posts(programs: list[models.Page], editor_id: int) -> None:
    if not programs or any(models.list_posts_by_program(p.id) for p in programs):
        print("Posts already seeded (or no programs to seed under), leaving as-is.")
        return

    for i, program in enumerate(programs):
        topic = POST_TOPICS[i % len(POST_TOPICS)]
        status = POST_STATUSES[i % len(POST_STATUSES)]
        title = f"My first week at {program.title}"
        post = models.create_post(
            program_id=program.id, title=title, body=_placeholder_body(title),
            topic=topic, author_id=editor_id,
        )
        if status in ("pending", "published"):
            models.set_post_status(post.id, from_status="draft", to_status="pending")
        if status == "published":
            models.set_post_status(post.id, from_status="pending", to_status="published")
    print(f"Seeded {len(programs)} posts across Topics and statuses "
          "(draft/pending/published) under the seeded Programs.")


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
    editor = models.get_user_by_email("editor@example.test")
    programs = _seed_pages(admin.id)
    _seed_posts(programs, editor.id)
    return 0


if __name__ == "__main__":
    sys.exit(main())
