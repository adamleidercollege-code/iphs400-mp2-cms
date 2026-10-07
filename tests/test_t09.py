"""T09 [stretch] (#10): client-side site search against a JSON index built
at `cms publish` time — no server-side search component."""
from __future__ import annotations

import json

from app import models
from app.publish import render_site
from app.services import markdown
from tests.conftest import _csrf_token_from


def _seed_program(author_id: int) -> models.Page:
    home = models.ensure_home_page()
    continent = models.publish_page(
        models.create_page(home.id, "Asia", "", False, author_id).id
    )
    country = models.publish_page(
        models.create_page(continent.id, "Japan", "", False, author_id).id
    )
    return models.publish_page(
        models.create_page(country.id, "Kyoto Exchange", "", False, author_id).id
    )


def _admin_csrf(c) -> str:
    return _csrf_token_from(c.get("/admin").text)


def _publish_post(c, post: models.Post) -> models.Post:
    token = _admin_csrf(c)
    c.post(f"/admin/posts/{post.id}/publish", data={"csrf_token": token})
    return models.get_post_by_id(post.id)


# -- app.services.markdown.plain_text: the full-body pipeline excerpt shares -


def test_plain_text_strips_markdown_markers_without_truncating():
    body = "# Heading\n\nSome **bold** text with a [link](http://x.test) and more words."
    plain = markdown.plain_text(body)
    assert "#" not in plain and "**" not in plain and "[" not in plain
    assert "Heading" in plain and "bold" in plain and "link" in plain
    assert "…" not in plain  # plain_text never truncates; excerpt does


# -- app.services.search_index.build_index: the pure data shape -------------


def test_index_contains_only_published_posts_with_title_text_and_tags(client_as, tmp_path):
    visa = models.create_tag("visa")
    admin_c = client_as("admin")
    admin = models.get_user_by_email("admin@example.test")
    program = _seed_program(admin.id)

    new_page = admin_c.get(f"/admin/posts/new?program_id={program.id}")
    token = _csrf_token_from(new_page.text)
    admin_c.post("/admin/posts/new", data={
        "program_id": str(program.id), "title": "Finding Housing",
        "body": "Housing here is **tricky** at first.", "topic": "housing",
        "tag_ids": [str(visa.id)], "action": "save", "csrf_token": token,
    })
    post = models.list_posts_by_program(program.id)[0]
    _publish_post(admin_c, post)

    out = render_site(tmp_path / "site")
    entries = json.loads((out / "search-index.json").read_text())

    assert len(entries) == 1
    entry = entries[0]
    assert entry["title"] == "Finding Housing"
    assert "tricky" in entry["text"]
    assert "**" not in entry["text"]  # markdown stripped, not raw
    assert entry["tags"] == ["visa"]
    assert entry["chain"] == ["asia", "japan", "kyoto-exchange"]
    assert entry["href"] == "asia/japan/kyoto-exchange/finding-housing/index.html"
    assert not entry["href"].startswith("/")  # relative, hard constraint
    assert (out / entry["href"]).exists()


def test_draft_and_pending_posts_never_reach_the_index(client_as, tmp_path):
    admin_c = client_as("admin")
    admin = models.get_user_by_email("admin@example.test")
    program = _seed_program(admin.id)

    draft = models.create_post(program.id, "Still A Draft", "draft body", "general", admin.id)
    pending = models.create_post(program.id, "Awaiting Review", "pending body", "general", admin.id)
    pending = models.set_post_status(pending.id, from_status="draft", to_status="pending")
    published = models.create_post(program.id, "Already Live", "live body", "general", admin.id)
    _publish_post(admin_c, published)

    out = render_site(tmp_path / "site")
    entries = json.loads((out / "search-index.json").read_text())
    titles = {e["title"] for e in entries}

    assert titles == {"Already Live"}
    assert draft.status == "draft" and pending.status == "pending"  # sanity


def test_unpublished_program_contributes_no_entries(client_as, tmp_path):
    """A Post can only be published under a published Program (same gate
    app.publish.render_site itself applies to HTML) — the index must not leak
    one whose parent Program never went live."""
    admin = models.get_user_by_email("admin@example.test")
    home = models.ensure_home_page()
    continent = models.publish_page(models.create_page(home.id, "Africa", "", False, admin.id).id)
    country = models.publish_page(models.create_page(continent.id, "Kenya", "", False, admin.id).id)
    draft_program = models.create_page(country.id, "Nairobi Fieldwork", "", False, admin.id)
    post = models.create_post(draft_program.id, "Orphaned Post", "x", "general", admin.id)
    models.set_post_status(post.id, from_status="draft", to_status="pending")
    models.set_post_status(post.id, from_status="pending", to_status="published")

    out = render_site(tmp_path / "site")
    entries = json.loads((out / "search-index.json").read_text())
    assert entries == []


# -- search boxes in the rendered templates ----------------------------------


def test_sitewide_search_box_is_on_every_public_page(client_as, tmp_path):
    admin_c = client_as("admin")
    admin = models.get_user_by_email("admin@example.test")
    program = _seed_program(admin.id)
    new_page = admin_c.get(f"/admin/posts/new?program_id={program.id}")
    token = _csrf_token_from(new_page.text)
    admin_c.post("/admin/posts/new", data={
        "program_id": str(program.id), "title": "A Post", "body": "x",
        "topic": "general", "action": "save", "csrf_token": token,
    })
    post = models.list_posts_by_program(program.id)[0]
    _publish_post(admin_c, post)

    out = render_site(tmp_path / "site")
    for path in [
        out / "index.html",
        out / "asia" / "index.html",
        out / "asia" / "japan" / "kyoto-exchange" / "index.html",
        out / "asia" / "japan" / "kyoto-exchange" / "a-post" / "index.html",
    ]:
        html = path.read_text()
        assert 'class="site-search site-search--header"' in html, path
        assert 'value="title"' in html and 'value="text"' in html and 'value="tags"' in html


def test_scoped_search_box_only_on_continent_country_program_pages(client_as, tmp_path):
    admin_c = client_as("admin")
    admin = models.get_user_by_email("admin@example.test")
    program = _seed_program(admin.id)
    new_page = admin_c.get(f"/admin/posts/new?program_id={program.id}")
    token = _csrf_token_from(new_page.text)
    admin_c.post("/admin/posts/new", data={
        "program_id": str(program.id), "title": "A Post", "body": "x",
        "topic": "general", "action": "save", "csrf_token": token,
    })
    post = models.list_posts_by_program(program.id)[0]
    _publish_post(admin_c, post)

    out = render_site(tmp_path / "site")
    home_html = (out / "index.html").read_text()
    assert 'site-search--scoped' not in home_html

    continent_html = (out / "asia" / "index.html").read_text()
    assert 'data-search-scope="asia"' in continent_html

    country_html = (out / "asia" / "japan" / "index.html").read_text()
    assert 'data-search-scope="asia/japan"' in country_html

    program_html = (out / "asia" / "japan" / "kyoto-exchange" / "index.html").read_text()
    assert 'data-search-scope="asia/japan/kyoto-exchange"' in program_html

    post_html = (out / "asia" / "japan" / "kyoto-exchange" / "a-post" / "index.html").read_text()
    assert 'site-search--scoped' not in post_html


def test_search_index_json_is_linked_relatively_not_root_absolute(client_as, tmp_path):
    admin = models.get_user_by_email("admin@example.test")
    _seed_program(admin.id)
    out = render_site(tmp_path / "site")

    home = (out / "index.html").read_text()
    assert 'search-index.json' in home
    assert 'href="/search-index.json"' not in home
    assert 'indexUrl: "search-index.json"' in home

    nested = (out / "asia" / "japan" / "index.html").read_text()
    assert 'indexUrl: "../../search-index.json"' in nested


# -- live preview: the same shape, built from the database ------------------


def test_live_preview_serves_the_same_index_shape(client_as):
    visa = models.create_tag("visa")
    admin_c = client_as("admin")
    admin = models.get_user_by_email("admin@example.test")
    program = _seed_program(admin.id)
    new_page = admin_c.get(f"/admin/posts/new?program_id={program.id}")
    token = _csrf_token_from(new_page.text)
    admin_c.post("/admin/posts/new", data={
        "program_id": str(program.id), "title": "Finding Housing", "body": "x",
        "topic": "housing", "tag_ids": [str(visa.id)], "action": "save", "csrf_token": token,
    })
    post = models.list_posts_by_program(program.id)[0]
    _publish_post(admin_c, post)

    response = admin_c.get("/search-index.json")
    assert response.status_code == 200
    entries = response.json()
    assert len(entries) == 1
    assert entries[0]["title"] == "Finding Housing"
    assert entries[0]["tags"] == ["visa"]
    assert entries[0]["href"] == "/asia/japan/kyoto-exchange/finding-housing/"
