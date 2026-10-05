"""T02: Pages — the content tree, authoring, and early cms publish."""
from __future__ import annotations

from app import models
from app.services import slugs
from tests.conftest import _csrf_token_from


def _admin_csrf(c) -> str:
    """A valid CSRF token for an already-logged-in client, from a page that
    always renders one — unlike /admin/pages, which only embeds one inside a
    per-draft publish form."""
    return _csrf_token_from(c.get("/admin").text)


def _create_page(c, parent_id, title, show_in_footer=False):
    page = c.get(f"/admin/pages/new?parent_id={parent_id}")
    token = _csrf_token_from(page.text)
    data = {"parent_id": str(parent_id), "title": title, "body": f"Body for {title}",
            "csrf_token": token}
    if show_in_footer:
        data["show_in_footer"] = "on"
    return c.post("/admin/pages/new", data=data, follow_redirects=False)


def test_admin_creates_a_nested_page(client_as):
    c = client_as("admin")
    home = models.ensure_home_page()
    response = _create_page(c, home.id, "Asia")
    assert response.status_code == 303

    asia = models.get_child_by_slug(home.id, "asia")
    assert asia is not None
    assert asia.status == "draft"
    assert asia.title == "Asia"


def test_admin_creates_a_standalone_footer_page(client_as):
    c = client_as("admin")
    home = models.ensure_home_page()
    _create_page(c, home.id, "About CGE", show_in_footer=True)

    about = models.get_child_by_slug(home.id, "about-cge")
    assert about.show_in_footer is True


def test_delete_requires_confirmation_then_deletes(client_as):
    c = client_as("admin")
    home = models.ensure_home_page()
    _create_page(c, home.id, "Scratch Page")
    page = models.get_child_by_slug(home.id, "scratch-page")

    confirm = c.get(f"/admin/pages/{page.id}/delete")
    assert confirm.status_code == 200
    assert "are you sure" in confirm.text.lower()

    token = _csrf_token_from(confirm.text)
    response = c.post(f"/admin/pages/{page.id}/delete",
                       data={"csrf_token": token}, follow_redirects=False)
    assert response.status_code == 303
    assert models.get_page_by_id(page.id) is None


def test_slug_regenerates_while_draft_then_freezes_on_publish(client_as):
    c = client_as("admin")
    home = models.ensure_home_page()
    _create_page(c, home.id, "First Title")
    page = models.get_child_by_slug(home.id, "first-title")
    assert page.slug == "first-title"

    edit_page = c.get(f"/admin/pages/{page.id}/edit")
    token = _csrf_token_from(edit_page.text)
    c.post(f"/admin/pages/{page.id}/edit",
           data={"title": "Renamed Title", "body": "x", "csrf_token": token},
           follow_redirects=False)
    renamed = models.get_page_by_id(page.id)
    assert renamed.slug == "renamed-title"

    token = _admin_csrf(c)
    c.post(f"/admin/pages/{page.id}/publish", data={"csrf_token": token},
           follow_redirects=False)

    edit_page = c.get(f"/admin/pages/{page.id}/edit")
    token = _csrf_token_from(edit_page.text)
    c.post(f"/admin/pages/{page.id}/edit",
           data={"title": "Title After Publish", "body": "x", "csrf_token": token},
           follow_redirects=False)
    after_publish = models.get_page_by_id(page.id)
    assert after_publish.title == "Title After Publish"
    assert after_publish.slug == "renamed-title"  # frozen


def test_editor_blocked_from_page_authoring_routes(client_as):
    c = client_as("editor")
    home = models.ensure_home_page()
    assert c.get("/admin/pages").status_code == 403
    assert c.get(f"/admin/pages/new?parent_id={home.id}").status_code == 403


def test_anonymous_redirected_to_login_for_page_authoring_routes(client):
    response = client.get("/admin/pages", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_publish_writes_only_published_pages_with_relative_links(client_as, tmp_path):
    from app.publish import render_site

    c = client_as("admin")
    home = models.ensure_home_page()
    _create_page(c, home.id, "Asia")
    asia = models.get_child_by_slug(home.id, "asia")
    token = _admin_csrf(c)
    c.post(f"/admin/pages/{asia.id}/publish", data={"csrf_token": token})

    _create_page(c, home.id, "Still Draft")

    out = render_site(tmp_path / "site")
    assert (out / "asia" / "index.html").exists()
    assert not (out / "still-draft").exists()

    asia_html = (out / "asia" / "index.html").read_text()
    assert 'href="/' not in asia_html and 'src="/' not in asia_html
    assert "../style.css" in asia_html
    assert "../index.html" in asia_html  # nav link back to Home


def test_footer_flagged_page_appears_sitewide_in_footer(client_as, tmp_path):
    from app.publish import render_site

    c = client_as("admin")
    home = models.ensure_home_page()
    _create_page(c, home.id, "Contact Us", show_in_footer=True)
    contact = models.get_child_by_slug(home.id, "contact-us")
    token = _admin_csrf(c)
    c.post(f"/admin/pages/{contact.id}/publish", data={"csrf_token": token})

    out = render_site(tmp_path / "site")
    home_html = (out / "index.html").read_text()
    assert "Contact Us" in home_html
    # Footer-flagged pages are excluded from Home's own child listing.
    assert 'href="contact-us/' not in home_html.split("<footer")[0]


def test_live_preview_matches_publish_visibility(client_as):
    c = client_as("admin")
    home = models.ensure_home_page()
    _create_page(c, home.id, "Live Draft")
    draft = models.get_child_by_slug(home.id, "live-draft")

    assert c.get("/live-draft/").status_code == 404

    token = _admin_csrf(c)
    c.post(f"/admin/pages/{draft.id}/publish", data={"csrf_token": token})
    assert c.get("/live-draft/").status_code == 200


def test_create_with_nonexistent_parent_is_404_not_a_crash(client_as):
    c = client_as("admin")
    assert c.get("/admin/pages/new?parent_id=999999").status_code == 404

    token = _admin_csrf(c)
    response = c.post(
        "/admin/pages/new",
        data={"parent_id": "999999", "title": "Orphan", "body": "x",
              "csrf_token": token},
    )
    assert response.status_code == 404


def test_edit_nonexistent_page_is_404_not_a_crash(client_as):
    c = client_as("admin")
    assert c.get("/admin/pages/999999/edit").status_code == 404


def test_home_page_cannot_be_deleted(client_as):
    c = client_as("admin")
    home = models.ensure_home_page()
    assert c.get(f"/admin/pages/{home.id}/delete").status_code == 400

    token = _admin_csrf(c)
    response = c.post(f"/admin/pages/{home.id}/delete", data={"csrf_token": token})
    assert response.status_code == 400
    assert models.get_page_by_id(home.id) is not None


# -- Services seam: pure functions, no HTTP or DB --------------------------

def test_slugify_collapses_non_alnum_runs():
    assert slugs.slugify("Kyoto Exchange!!") == "kyoto-exchange"
    assert slugs.slugify("  Leading/Trailing  ") == "leading-trailing"


def test_slugify_empty_title_falls_back():
    assert slugs.slugify("???") == "page"


def test_dedupe_appends_numeric_suffix():
    assert slugs.dedupe("asia", set()) == "asia"
    assert slugs.dedupe("asia", {"asia"}) == "asia-2"
    assert slugs.dedupe("asia", {"asia", "asia-2"}) == "asia-3"
