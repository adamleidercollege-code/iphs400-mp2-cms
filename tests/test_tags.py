"""Tags on posts (#14): a Staff-curated, multi-select label set, distinct
from Topic (CONTEXT.md)."""
from __future__ import annotations

import importlib.util
import re
from pathlib import Path

from app import models
from app.publish import render_site
from tests.conftest import _csrf_token_from

_ROOT = Path(__file__).resolve().parents[1]


def _checked_tag_ids(html: str) -> set[str]:
    """Which `tag_ids` checkboxes posts_form.html pre-checks, read straight
    from the rendered HTML rather than assumed from context."""
    return set(re.findall(r'name="tag_ids" value="(\d+)"\s+checked', html))


def _load_seed_demo():
    """scripts/ isn't a package (see tests/test_usage_report.py for prior art)."""
    spec = importlib.util.spec_from_file_location(
        "seed_demo", _ROOT / "scripts" / "seed_demo.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _admin_csrf(c) -> str:
    return _csrf_token_from(c.get("/admin").text)


def _seed_program(author_id: int) -> models.Page:
    """Home -> Continent -> Country -> Program, each published — the Topic
    filter's own render_site tests (test_t03.py) never publish, since they
    only exercise the live DB, but a static export skips an unpublished Page
    entirely, so this module's export-backed tests need every ancestor live."""
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


def _create_tag(c, name: str):
    page = c.get("/admin/tags/new")
    token = _csrf_token_from(page.text)
    return c.post("/admin/tags/new", data={"name": name, "csrf_token": token},
                  follow_redirects=False)


# -- Staff manages the shared vocabulary --------------------------------------


def test_staff_creates_renames_and_deletes_a_tag(client_as):
    c = client_as("admin")
    response = _create_tag(c, "visa")
    assert response.status_code == 303

    tag = models.list_tags()[0]
    assert tag.name == "visa"

    edit_page = c.get(f"/admin/tags/{tag.id}/edit")
    assert edit_page.status_code == 200
    token = _csrf_token_from(edit_page.text)
    c.post(f"/admin/tags/{tag.id}/edit",
           data={"name": "visa-renamed", "csrf_token": token}, follow_redirects=False)
    assert models.get_tag_by_id(tag.id).name == "visa-renamed"

    confirm = c.get(f"/admin/tags/{tag.id}/delete")
    assert confirm.status_code == 200
    assert "are you sure" in confirm.text.lower()
    token = _csrf_token_from(confirm.text)
    response = c.post(f"/admin/tags/{tag.id}/delete",
                       data={"csrf_token": token}, follow_redirects=False)
    assert response.status_code == 303
    assert models.get_tag_by_id(tag.id) is None


def test_duplicate_tag_name_is_rejected(client_as):
    c = client_as("admin")
    _create_tag(c, "budget")
    response = _create_tag(c, "budget")
    assert response.status_code == 400
    assert "already exists" in response.text.lower()
    assert len(models.list_tags()) == 1


def test_empty_tag_name_is_rejected(client_as):
    c = client_as("admin")
    response = _create_tag(c, "   ")
    assert response.status_code == 400
    assert models.list_tags() == []


# -- An Ambassador is blocked from the Tags screen entirely -------------------


def test_ambassador_cannot_create_rename_or_delete_a_tag(client_as):
    tag = models.create_tag("travel")
    c = client_as("editor")
    assert c.get("/admin/tags").status_code == 403
    assert c.get("/admin/tags/new").status_code == 403

    token = _admin_csrf(c)
    assert c.post("/admin/tags/new",
                   data={"name": "new-tag", "csrf_token": token}).status_code == 403
    assert c.get(f"/admin/tags/{tag.id}/edit").status_code == 403
    assert c.post(f"/admin/tags/{tag.id}/edit",
                   data={"name": "renamed", "csrf_token": token}).status_code == 403
    assert c.get(f"/admin/tags/{tag.id}/delete").status_code == 403
    assert c.post(f"/admin/tags/{tag.id}/delete",
                   data={"csrf_token": token}).status_code == 403
    assert models.list_tags() == [tag]


def test_anonymous_redirected_to_login_for_tag_routes(client):
    response = client.get("/admin/tags", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_tags_screen_only_in_staff_sidebar(client_as):
    assert "Tags" in client_as("admin").get("/admin/dashboard").text
    assert "Tags" not in client_as("editor").get("/admin").text


# -- Writing a Post: both roles pick from the existing list ------------------


def test_ambassador_picks_existing_tags_when_writing_a_post(client_as):
    visa = models.create_tag("visa")
    budget = models.create_tag("budget")
    admin = models.get_user_by_email("admin@example.test")
    program = _seed_program(admin.id)

    c = client_as("editor")
    new_page = c.get(f"/admin/posts/new?program_id={program.id}")
    assert f'value="{visa.id}"' in new_page.text
    assert f'value="{budget.id}"' in new_page.text

    token = _csrf_token_from(new_page.text)
    c.post("/admin/posts/new", data={
        "program_id": str(program.id), "title": "My Post", "body": "x",
        "topic": "housing", "tag_ids": [str(visa.id), str(budget.id)],
        "action": "save", "csrf_token": token,
    }, follow_redirects=False)

    post = models.list_posts_by_program(program.id)[0]
    assert {t.name for t in models.get_tags_for_post(post.id)} == {"visa", "budget"}


def test_editing_a_post_replaces_its_tag_set(client_as):
    visa = models.create_tag("visa")
    budget = models.create_tag("budget")
    admin = models.get_user_by_email("admin@example.test")
    program = _seed_program(admin.id)
    c = client_as("editor")

    new_page = c.get(f"/admin/posts/new?program_id={program.id}")
    token = _csrf_token_from(new_page.text)
    c.post("/admin/posts/new", data={
        "program_id": str(program.id), "title": "My Post", "body": "x",
        "topic": "housing", "tag_ids": [str(visa.id)],
        "action": "save", "csrf_token": token,
    })
    post = models.list_posts_by_program(program.id)[0]
    assert {t.id for t in models.get_tags_for_post(post.id)} == {visa.id}

    edit_page = c.get(f"/admin/posts/{post.id}/edit")
    assert _checked_tag_ids(edit_page.text) == {str(visa.id)}
    token = _csrf_token_from(edit_page.text)
    c.post(f"/admin/posts/{post.id}/edit", data={
        "title": "My Post", "body": "x", "topic": "housing",
        "tag_ids": [str(budget.id)], "action": "save", "csrf_token": token,
    })
    assert {t.id for t in models.get_tags_for_post(post.id)} == {budget.id}


def test_a_deleted_tag_id_submitted_with_the_post_form_is_dropped_not_500(client_as):
    """A tampered or stale request could submit a tag_ids value that no
    longer exists (e.g. another tab deleted it first); the route should drop
    it rather than hit the tags.post_tags foreign key and 500."""
    gone = models.create_tag("gone")
    admin = models.get_user_by_email("admin@example.test")
    program = _seed_program(admin.id)
    c = client_as("editor")
    models.delete_tag(gone.id)

    new_page = c.get(f"/admin/posts/new?program_id={program.id}")
    token = _csrf_token_from(new_page.text)
    response = c.post("/admin/posts/new", data={
        "program_id": str(program.id), "title": "Tampered", "body": "x",
        "topic": "general", "tag_ids": [str(gone.id)],
        "action": "save", "csrf_token": token,
    }, follow_redirects=False)
    assert response.status_code == 303
    post = models.list_posts_by_program(program.id)[0]
    assert models.get_tags_for_post(post.id) == []


def test_post_with_no_tags_saves_cleanly(client_as):
    admin = models.get_user_by_email("admin@example.test")
    program = _seed_program(admin.id)
    c = client_as("editor")

    new_page = c.get(f"/admin/posts/new?program_id={program.id}")
    token = _csrf_token_from(new_page.text)
    response = c.post("/admin/posts/new", data={
        "program_id": str(program.id), "title": "Untagged", "body": "x",
        "topic": "general", "action": "save", "csrf_token": token,
    }, follow_redirects=False)
    assert response.status_code == 303
    post = models.list_posts_by_program(program.id)[0]
    assert models.get_tags_for_post(post.id) == []


# -- Public site: tags show on cards/pages and drive a Program-page filter ---


def test_tags_show_on_post_cards_and_the_post_page(client_as, tmp_path):
    visa = models.create_tag("visa")
    admin_c = client_as("admin")
    admin = models.get_user_by_email("admin@example.test")
    program = _seed_program(admin.id)

    new_page = admin_c.get(f"/admin/posts/new?program_id={program.id}")
    token = _csrf_token_from(new_page.text)
    admin_c.post("/admin/posts/new", data={
        "program_id": str(program.id), "title": "Visa Day", "body": "x",
        "topic": "other", "tag_ids": [str(visa.id)],
        "action": "save", "csrf_token": token,
    })
    post = models.list_posts_by_program(program.id)[0]
    token = _admin_csrf(admin_c)
    admin_c.post(f"/admin/posts/{post.id}/publish", data={"csrf_token": token})

    out = render_site(tmp_path / "site")
    program_html = (out / "asia" / "japan" / "kyoto-exchange" / "index.html").read_text()
    assert 'class="tag-badge">visa<' in program_html

    post_html = (
        out / "asia" / "japan" / "kyoto-exchange" / "visa-day" / "index.html"
    ).read_text()
    assert 'class="tag-badge">visa<' in post_html


def test_program_page_tag_filter_lists_only_tags_in_use(client_as, tmp_path):
    visa = models.create_tag("visa")
    models.create_tag("unused-tag")
    admin_c = client_as("admin")
    admin = models.get_user_by_email("admin@example.test")
    program = _seed_program(admin.id)

    new_page = admin_c.get(f"/admin/posts/new?program_id={program.id}")
    token = _csrf_token_from(new_page.text)
    admin_c.post("/admin/posts/new", data={
        "program_id": str(program.id), "title": "Visa Day", "body": "x",
        "topic": "other", "tag_ids": [str(visa.id)],
        "action": "save", "csrf_token": token,
    })
    post = models.list_posts_by_program(program.id)[0]
    token = _admin_csrf(admin_c)
    admin_c.post(f"/admin/posts/{post.id}/publish", data={"csrf_token": token})

    out = render_site(tmp_path / "site")
    html = (out / "asia" / "japan" / "kyoto-exchange" / "index.html").read_text()
    assert 'class="tag-filters"' in html
    assert f'data-tag="{visa.id}"' in html
    assert ">visa<" in html
    assert "unused-tag" not in html


def test_program_page_has_no_tag_filter_when_no_posts_are_tagged(client_as, tmp_path):
    models.create_tag("visa")
    admin_c = client_as("admin")
    admin = models.get_user_by_email("admin@example.test")
    program = _seed_program(admin.id)

    new_page = admin_c.get(f"/admin/posts/new?program_id={program.id}")
    token = _csrf_token_from(new_page.text)
    admin_c.post("/admin/posts/new", data={
        "program_id": str(program.id), "title": "No Tags Here", "body": "x",
        "topic": "general", "action": "save", "csrf_token": token,
    })
    post = models.list_posts_by_program(program.id)[0]
    token = _admin_csrf(admin_c)
    admin_c.post(f"/admin/posts/{post.id}/publish", data={"csrf_token": token})

    out = render_site(tmp_path / "site")
    html = (out / "asia" / "japan" / "kyoto-exchange" / "index.html").read_text()
    assert 'class="tag-filters"' not in html


# -- scripts/seed_demo.py: starter tags, applied to the demo catalog ---------


def test_seed_demo_seeds_starter_tags_and_applies_them(client):
    seed_demo = _load_seed_demo()
    admin = models.get_user_by_email("admin@example.test")
    editor = models.get_user_by_email("editor@example.test")
    programs = seed_demo._seed_pages(admin.id)
    seed_demo._seed_posts(programs, editor.id)

    tag_names = {t.name for t in models.list_tags()}
    assert tag_names == set(seed_demo.TAG_NAMES)

    all_posts = [p for program in programs for p in models.list_posts_by_program(program.id)]
    tagged = [p for p in all_posts if models.get_tags_for_post(p.id)]
    assert tagged  # at least one seeded post carries a tag
    used_tag_names = {
        tag.name for p in all_posts for tag in models.get_tags_for_post(p.id)
    }
    assert used_tag_names == set(seed_demo.TAG_NAMES)  # every starter tag gets used
