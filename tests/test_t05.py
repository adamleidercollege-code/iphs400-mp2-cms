"""T05: Public Posts and cms publish extended."""
from __future__ import annotations

import importlib.util
import re
from pathlib import Path

from app import models
from tests.conftest import _csrf_token_from

_ROOT = Path(__file__).resolve().parents[1]


def _topic_section(html: str, topic: str) -> str:
    """The contents of one Topic's <section>, distinct from a same-named
    filter <button> (identified by its own "post-topic-group" class)."""
    match = re.search(
        rf'<section class="post-topic-group" data-topic="{topic}">(.*?)</section>',
        html, re.S,
    )
    assert match, f"no post-topic-group section for topic={topic!r}"
    return match.group(1)


def _admin_csrf(c) -> str:
    return _csrf_token_from(c.get("/admin").text)


def _seed_program(parent_author_id: int) -> models.Page:
    home = models.ensure_home_page()
    continent = models.create_page(home.id, "Asia", "", False, parent_author_id)
    country = models.create_page(continent.id, "Japan", "", False, parent_author_id)
    program = models.create_page(country.id, "Kyoto Exchange", "", False, parent_author_id)
    return models.publish_page(program.id)


def _create_post(c, program_id: int, title: str, topic: str = "housing") -> models.Post:
    page = c.get(f"/admin/posts/new?program_id={program_id}")
    token = _csrf_token_from(page.text)
    c.post(
        "/admin/posts/new",
        data={"program_id": str(program_id), "title": title, "body": "Hello there",
              "topic": topic, "action": "save", "csrf_token": token},
        follow_redirects=False,
    )
    return models.list_posts_by_program(program_id)[0]


def _publish_post(admin_c, post: models.Post) -> models.Post:
    models.set_post_status(post.id, from_status=post.status, to_status="pending")
    token = _csrf_token_from(admin_c.get(f"/admin/posts?program_id={post.program_id}").text)
    admin_c.post(f"/admin/posts/{post.id}/publish", data={"csrf_token": token})
    return models.get_post_by_id(post.id)


def _program_path(program: models.Page) -> str:
    return "/" + "/".join(a.slug for a in models.list_ancestors(program)[1:]) + f"/{program.slug}/"


# -- Live preview: grouped by Topic, filterable, drafts hidden --------------


def test_program_page_lists_published_posts_grouped_by_topic(client_as):
    c = client_as("admin")
    admin = models.get_user_by_email("admin@example.test")
    program = _seed_program(admin.id)

    housing = _create_post(c, program.id, "Finding an Apartment", topic="housing")
    meals = _create_post(c, program.id, "Favorite Ramen Shop", topic="meals")
    _publish_post(c, housing)
    _publish_post(c, meals)

    response = c.get(_program_path(program))
    assert response.status_code == 200
    # Each Post sits inside its OWN Topic's <section>, not just anywhere on
    # the page — a loose "is the word present" check wouldn't tell the two
    # Topics' Posts apart.
    housing_section = _topic_section(response.text, "housing")
    meals_section = _topic_section(response.text, "meals")
    assert "Finding an Apartment" in housing_section
    assert "Finding an Apartment" not in meals_section
    assert "Favorite Ramen Shop" in meals_section
    assert "Favorite Ramen Shop" not in housing_section
    # Topic filter pills are present, so a visitor can filter to one Topic.
    assert 'class="topic-pill" data-topic="housing"' in response.text
    assert 'data-topic="all"' in response.text


def test_draft_and_pending_posts_never_reach_a_public_response(client_as):
    c = client_as("admin")
    admin = models.get_user_by_email("admin@example.test")
    program = _seed_program(admin.id)

    draft = _create_post(c, program.id, "Still Writing This")
    pending = _create_post(c, program.id, "Submitted For Review")
    models.set_post_status(pending.id, from_status="draft", to_status="pending")

    response = c.get(_program_path(program))
    assert "Still Writing This" not in response.text
    assert "Submitted For Review" not in response.text

    # Not reachable directly by slug either.
    assert c.get(_program_path(program) + f"{draft.slug}/").status_code == 404
    assert c.get(_program_path(program) + f"{pending.slug}/").status_code == 404


def test_published_post_renders_sanitized_markdown(client_as):
    c = client_as("admin")
    admin = models.get_user_by_email("admin@example.test")
    program = _seed_program(admin.id)
    post = _create_post(c, program.id, "A Normal Title")
    models.update_post(post.id, title=post.title,
                        body="Hello <script>alert('x')</script> **world**", topic=post.topic)
    post = _publish_post(c, post)

    response = c.get(_program_path(program) + f"{post.slug}/")
    assert response.status_code == 200
    assert "<script>" not in response.text
    assert "<strong>world</strong>" in response.text


def test_post_slug_stays_frozen_through_a_title_edit_made_after_publish(client_as):
    c = client_as("admin")
    admin = models.get_user_by_email("admin@example.test")
    program = _seed_program(admin.id)
    post = _create_post(c, program.id, "Original Title")
    assert post.slug == "original-title"
    post = _publish_post(c, post)

    models.update_post(post.id, title="Renamed After Publish", body=post.body, topic=post.topic)
    after = models.get_post_by_id(post.id)
    assert after.title == "Renamed After Publish"
    assert after.slug == "original-title"  # frozen


# -- cms publish: static export ----------------------------------------------


def test_cms_publish_writes_published_posts_with_relative_links(client_as, tmp_path):
    from app.publish import render_site

    c = client_as("admin")
    admin = models.get_user_by_email("admin@example.test")
    program = _seed_program(admin.id)
    post = _create_post(c, program.id, "A Great Week", topic="social-life")
    post = _publish_post(c, post)
    draft = _create_post(c, program.id, "Not Ready Yet")

    out = render_site(tmp_path / "site")
    program_dir = out / "asia" / "japan" / "kyoto-exchange"
    post_html_path = program_dir / post.slug / "index.html"
    assert post_html_path.exists()
    assert not (program_dir / draft.slug).exists()

    program_html = (program_dir / "index.html").read_text()
    assert f'{post.slug}/index.html"' in program_html  # relative link to the post
    assert "Social Life" in program_html

    post_html = post_html_path.read_text()
    assert 'href="/' not in post_html and 'src="/' not in post_html
    assert "A Great Week" in post_html
    # A Post's page lives one level deeper than its Program (asia/japan/
    # kyoto-exchange/<slug>/), so every furniture link — breadcrumb included,
    # not just nav — must climb 4 "../", or it 404s from the deployed site.
    assert 'href="../../../../index.html"' in post_html  # breadcrumb: Home
    assert "../../../../style.css" in post_html


def test_seed_demo_posts_render_end_to_end_through_cms_publish(client, tmp_path):
    """scripts/ isn't a package (see tests/test_usage_report.py for prior art)."""
    spec = importlib.util.spec_from_file_location(
        "seed_demo", _ROOT / "scripts" / "seed_demo.py"
    )
    seed_demo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(seed_demo)

    from app.publish import render_site

    admin = models.get_user_by_email("admin@example.test")
    editor = models.get_user_by_email("editor@example.test")
    programs = seed_demo._seed_pages(admin.id)
    seed_demo._seed_posts(programs, editor.id)

    out = render_site(tmp_path / "site")
    published = [
        p for program in programs
        for p in models.list_published_posts_by_program(program.id)
    ]
    assert published
    for program in programs:
        program_chain = [a.slug for a in models.list_ancestors(program)[1:]] + [program.slug]
        for post in models.list_published_posts_by_program(program.id):
            post_path = out.joinpath(*program_chain, post.slug, "index.html")
            assert post_path.exists()
            html = post_path.read_text()
            assert 'href="/' not in html and 'src="/' not in html
