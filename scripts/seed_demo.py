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

# Continent -> Country -> Program -> body, each with its own clearly
# fictional description (T11 follow-up: no more "Placeholder copy").
CONTINENTS = {
    "Asia": {
        "description": (
            "Asia is home to CGE's two longest-running exchange partnerships, spanning a "
            "modern metropolis and a mountain-ringed former capital. Students here balance "
            "rigorous coursework with first-hand immersion in neighborhoods most visitors "
            "never see."
        ),
        "countries": {
            "Japan": {
                "description": (
                    "Kyoto's canals, temple gardens, and dense grid of family-run restaurants "
                    "make it one of the most walkable cities CGE sends students to. Expect a "
                    "slower pace outside the classroom, and a host-family culture that treats "
                    "language practice as a dinner-table sport."
                ),
                "programs": {
                    "Kyoto Exchange": (
                        "A semester based in the Higashiyama district, split between "
                        "Japanese-language seminars at a partner university and a weekly "
                        "fieldwork placement — recent cohorts have worked with a ceramics "
                        "studio, a city archive, and a neighborhood association planning a "
                        "summer festival."
                    ),
                },
            },
            "South Korea": {
                "description": (
                    "Seoul moves fast, and CGE's program is built around keeping up with it: "
                    "dense public transit, a 24-hour study-cafe culture, and a student body "
                    "that treats weekend hiking trips as seriously as exam prep."
                ),
                "programs": {
                    "Seoul Studies": (
                        "Coursework in Korean language and contemporary media runs alongside "
                        "an internship track — past placements include a webtoon publisher, "
                        "a language-exchange nonprofit, and a small-batch coffee roaster near "
                        "Hongdae."
                    ),
                },
            },
        },
    },
    "Africa": {
        "description": (
            "CGE's Africa partnerships sit on opposite coasts of the continent — a "
            "fieldwork-heavy program on the Indian Ocean side and an urban semester on the "
            "Atlantic side — and both lean on local organizations rather than a "
            "classroom-only model."
        ),
        "countries": {
            "Kenya": {
                "description": (
                    "Programs here are built around Nairobi's mix of university partnerships "
                    "and grassroots organizations, with fieldwork that regularly leaves the "
                    "city for rural sites a few hours out."
                ),
                "programs": {
                    "Nairobi Fieldwork": (
                        "Students split time between seminar coursework at a Nairobi partner "
                        "university and a placement with a community organization — recent "
                        "projects have covered water-access mapping, a youth sports league, "
                        "and a small-business microloan cooperative."
                    ),
                },
            },
            "South Africa": {
                "description": (
                    "Cape Town's program leans urban: coursework on the post-apartheid city, "
                    "internships across the city's nonprofit and arts sectors, and a long "
                    "list of weekend excursions along the coast."
                ),
                "programs": {
                    "Cape Town Semester": (
                        "A full semester combining university coursework with an internship "
                        "placement — students have worked with a township-based arts "
                        "nonprofit, a marine-conservation group, and a local radio station "
                        "covering city politics."
                    ),
                },
            },
        },
    },
    "Europe": {
        "description": (
            "CGE's two European programs sit at opposite ends of the academic spectrum — an "
            "intensive language immersion in Spain and a studio-and-seminar arts program in "
            "France — but both are built around small cohorts and a lot of independent city "
            "exploration."
        ),
        "countries": {
            "Spain": {
                "description": (
                    "Madrid's program is language-first: morning grammar and conversation "
                    "seminars, afternoons spent putting that Spanish to use across the city, "
                    "from the Mercado de San Miguel to the Reina Sofía."
                ),
                "programs": {
                    "Madrid Language Immersion": (
                        "An intensive Spanish-language track with a host-family placement, "
                        "built around daily conversation practice and a midterm research "
                        "project on a neighborhood of the student's choosing."
                    ),
                },
            },
            "France": {
                "description": (
                    "Paris Arts & Culture runs out of a partner institute near the Marais, "
                    "with coursework split between studio practice and art-history seminars "
                    "that make regular use of the city's museums."
                ),
                "programs": {
                    "Paris Arts & Culture": (
                        "A studio-and-seminar semester combining a working art studio, "
                        "museum-based art-history seminars, and a final portfolio show at the "
                        "partner institute."
                    ),
                },
            },
        },
    },
}

STANDALONE_PAGES = {
    "About CGE": (
        "The Kenyon Center for Global Engagement (CGE) connects Kenyon students with "
        "semester and year-long programs abroad, runs the campus's pre-departure and "
        "re-entry workshops, and advises students putting together a study-abroad plan "
        "that fits their major.\n\n"
        "This site is a demo build for IPHS 400 Mini-Project #2 — not an official Kenyon "
        "page — but the Continent, Country, and Program pages describe the kind of "
        "structure a real CGE site would have."
    ),
    "Contact Us": (
        "Reach the demo CGE office at **cge-demo@kenyon.edu** — a placeholder address; "
        "this is a class project, not a live inbox.\n\n"
        "The office is modeled on a ground-floor suite in Chalmers Library, open Monday "
        "through Friday, 9am to 4pm. Drop-in advising hours run Tuesday and Thursday "
        "afternoons; other times are by appointment."
    ),
}

# Cycled across the seeded Programs so posts land across different Topics
# (T03 acceptance: "a few draft Posts across different Topics").
POST_TOPICS = [value for value, _label in models.TOPIC_CHOICES]

# Cycled too, so the review-gate workflow (ADR-004) is visible on a fresh
# clone (T04 acceptance): at least one Post in each status.
POST_STATUSES = ["draft", "pending", "published"]

# Clearly fictional student Ambassadors who author the extra, always-published
# demo posts (T11 follow-up), so Program pages have more than one voice and
# the topic filter has something to show.
FICTIONAL_AMBASSADORS = [
    ("Maya Chen", "maya.chen@example.test"),
    ("Diego Ramirez", "diego.ramirez@example.test"),
    ("Amara Okafor", "amara.okafor@example.test"),
    ("Priya Patel", "priya.patel@example.test"),
    ("Liam O'Connor", "liam.oconnor@example.test"),
    ("Sofia Rossi", "sofia.rossi@example.test"),
]
FICTIONAL_AMBASSADOR_PASSWORD = "change-me-demo-ambassador"

TOPIC_POST_TITLES = {
    "general": "Settling in",
    "housing": "Finding a place to live",
    "meals": "What's actually on the menu",
    "social-life": "The weekend group chat",
    "academics": "How the coursework compares",
    "other": "Odds and ends from the first month",
}


def _topic_post_body(topic: str, program_title: str) -> str:
    bodies = {
        "general": (
            f"The first two weeks with **{program_title}** were mostly logistics — figuring "
            "out the transit pass, finding the closest grocery store, and learning which "
            "office handles what. It's starting to feel less like a trip and more like an "
            "actual routine."
        ),
        "housing": (
            f"Moving in for **{program_title}** meant a week of comparing notes with other "
            "students about host families versus the dorm option. The host-family route won "
            "out for the extra conversation practice, even giving up a kitchen of my own."
        ),
        "meals": (
            f"Dining through **{program_title}** has turned into its own research project. "
            "The cafeteria is fine in a pinch, but the real finds have come from a market two "
            "blocks over that a classmate pointed me toward during orientation week."
        ),
        "social-life": (
            f"Between classes, **{program_title}** has a surprisingly active group chat — "
            "mostly for organizing weekend trips, but also for splitting the cost of things "
            "nobody wants to buy alone. It's made the first month feel a lot less isolating."
        ),
        "academics": (
            f"Coursework through **{program_title}** runs differently than a Kenyon semester "
            "— fewer weekly problem sets, more long-form projects due at the end of the term. "
            "It took a few weeks to adjust the study schedule accordingly."
        ),
        "other": (
            f"A few things from **{program_title}** that didn't fit anywhere else: the power "
            "adapters everyone forgets, the laundry schedule nobody explains in advance, and "
            "office hours that work nothing like they do back home."
        ),
    }
    return bodies[topic]


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

    def _add(parent_id: int, title: str, body: str, show_in_footer: bool = False) -> models.Page:
        page = models.create_page(
            parent_id=parent_id, title=title, body=body,
            show_in_footer=show_in_footer, author_id=admin_id,
        )
        return models.publish_page(page.id)

    programs: list[models.Page] = []
    for continent_title, continent_data in CONTINENTS.items():
        continent = _add(home.id, continent_title, continent_data["description"])
        for country_title, country_data in continent_data["countries"].items():
            country = _add(continent.id, country_title, country_data["description"])
            for program_title, program_body in country_data["programs"].items():
                programs.append(_add(country.id, program_title, program_body))

    for standalone_title, body in STANDALONE_PAGES.items():
        _add(home.id, standalone_title, body, show_in_footer=True)

    print("Seeded the Continent -> Country -> Program tree and standalone pages.")
    return programs


def _ensure_fictional_ambassadors() -> list[models.User]:
    users = []
    for name, email in FICTIONAL_AMBASSADORS:
        user = models.get_user_by_email(email)
        if user is None:
            user = models.create_user(
                email=email, password=FICTIONAL_AMBASSADOR_PASSWORD,
                role="editor", display_name=name,
            )
        users.append(user)
    return users


def _seed_posts(programs: list[models.Page], editor_id: int) -> None:
    """Three posts per Program: one from the Ambassador Demo account (cycling
    Topic and Status, so every status and multiple Topics show up across the
    catalog for the admin side to exercise), plus two always-PUBLISHED posts
    from different fictional Ambassadors across two more Topics, so every
    Program page actually has something in its topic filter and post grid.
    """
    if not programs or any(models.list_posts_by_program(p.id) for p in programs):
        print("Posts already seeded (or no programs to seed under), leaving as-is.")
        return

    ambassadors = _ensure_fictional_ambassadors()

    for i, program in enumerate(programs):
        anchor_topic = POST_TOPICS[i % len(POST_TOPICS)]
        status = POST_STATUSES[i % len(POST_STATUSES)]
        anchor_title = f"My first week at {program.title}"
        anchor = models.create_post(
            program_id=program.id, title=anchor_title,
            body=_topic_post_body(anchor_topic, program.title),
            topic=anchor_topic, author_id=editor_id,
        )
        if status in ("pending", "published"):
            models.set_post_status(anchor.id, from_status="draft", to_status="pending")
        if status == "published":
            models.set_post_status(anchor.id, from_status="pending", to_status="published")

        for offset in (2, 4):
            topic = POST_TOPICS[(i + offset) % len(POST_TOPICS)]
            author = ambassadors[(i * 2 + offset // 2) % len(ambassadors)]
            title = f"{TOPIC_POST_TITLES[topic]} — {program.title}"
            post = models.create_post(
                program_id=program.id, title=title,
                body=_topic_post_body(topic, program.title),
                topic=topic, author_id=author.id,
            )
            models.set_post_status(post.id, from_status="draft", to_status="pending")
            models.set_post_status(post.id, from_status="pending", to_status="published")

    print(f"Seeded {len(programs) * 3} posts across Topics and statuses "
          "(draft/pending/published) under the seeded Programs.")


def _seed_deactivated_users_with_drafts(programs: list[models.Page]) -> None:
    """T06 acceptance: one already-deactivated Ambassador and one
    already-deactivated Staff member, each seeded by creating the account
    active, giving them a draft Post, and then deactivating them — so the
    cascade actually runs rather than just hard-coding the end state. The
    Ambassador's draft is deleted by the cascade; the Staff member's is left
    in place, same as any other Staff member's unfinished work.
    """
    if not programs:
        print("No programs to seed deactivated-user drafts under, leaving as-is.")
        return
    if models.get_user_by_email("deactivated-ambassador@example.test") is not None:
        print("Deactivated demo users already seeded, leaving as-is.")
        return

    program = programs[0]
    ambassador = models.create_user(
        email="deactivated-ambassador@example.test", password="change-me-deactivated",
        role="editor", display_name="Former Ambassador",
    )
    models.create_post(
        program_id=program.id, title="Half-finished post",
        body="Still drafting — notes to self before writing the real thing.",
        topic="general", author_id=ambassador.id,
    )
    models.deactivate_user(ambassador.id)

    staff = models.create_user(
        email="deactivated-staff@example.test", password="change-me-deactivated",
        role="admin", display_name="Former Staff",
    )
    models.create_post(
        program_id=program.id, title="CGE's unfinished draft",
        body="Still drafting — notes to self before writing the real thing.",
        topic="general", author_id=staff.id,
    )
    models.deactivate_user(staff.id)

    print("Seeded a deactivated Ambassador (draft deleted by the cascade) and "
          "a deactivated Staff member (draft left in place).")


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
    _seed_deactivated_users_with_drafts(programs)
    return 0


if __name__ == "__main__":
    sys.exit(main())
