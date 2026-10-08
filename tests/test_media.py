"""Media uploads with alt text and cover images (#15).

Covers upload validation, the alt-text requirement, permissions (an
Ambassador can't set a Program's cover image or touch another author's
Post), and that a draft's images are never published.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from app import models, settings
from app.publish import render_site
from app.services import markdown, media_store, placeholder_image
from tests.conftest import _csrf_token_from

_ROOT = Path(__file__).resolve().parents[1]


def _valid_png() -> bytes:
    return placeholder_image.gradient_png(8, 8, (10, 20, 30), (40, 50, 60))


def _valid_jpeg() -> bytes:
    return b"\xff\xd8\xff" + b"\x00" * 64


def _valid_webp() -> bytes:
    return b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"\x00" * 32


def _not_an_image() -> bytes:
    return b"just some ordinary text, not an image at all"


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
    """Home -> Continent -> Country -> Program, each published — a static
    export (render_site) skips an unpublished Page entirely, so any test
    that calls it needs every ancestor live."""
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


def _create_draft_post(c, program_id: int, title: str = "My Post") -> models.Post:
    new_page = c.get(f"/admin/posts/new?program_id={program_id}")
    token = _csrf_token_from(new_page.text)
    c.post("/admin/posts/new", data={
        "program_id": str(program_id), "title": title, "body": "x",
        "topic": "general", "action": "save", "csrf_token": token,
    })
    return models.list_posts_by_program(program_id)[0]


# -- Upload validation --------------------------------------------------------


def test_save_upload_rejects_a_non_image_file(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "MEDIA_DIR", tmp_path)
    with pytest.raises(media_store.UploadRejected):
        media_store.save_upload(_not_an_image(), uploaded_by=None)


def test_save_upload_rejects_oversized_file(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "MEDIA_DIR", tmp_path)
    oversized = _valid_png() + b"\x00" * media_store.MAX_SIZE
    with pytest.raises(media_store.UploadRejected):
        media_store.save_upload(oversized, uploaded_by=None)


def test_save_upload_rejects_empty_file(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "MEDIA_DIR", tmp_path)
    with pytest.raises(media_store.UploadRejected):
        media_store.save_upload(b"", uploaded_by=None)


def test_save_upload_accepts_jpg_png_and_webp_by_real_content_not_claimed_type(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(settings, "MEDIA_DIR", tmp_path)
    for data, expected_type in [
        (_valid_jpeg(), "image/jpeg"),
        (_valid_png(), "image/png"),
        (_valid_webp(), "image/webp"),
    ]:
        filename, content_type, size = media_store.save_upload(data, uploaded_by=None)
        assert content_type == expected_type
        assert size == len(data)
        assert (settings.MEDIA_DIR / filename).read_bytes() == data


def test_save_upload_ignores_the_original_filename_entirely(tmp_path, monkeypatch):
    """The route never even collects a filename from the browser (only the
    bytes and alt text) — save_upload always generates one, so the original
    name an attacker or a careless upload might carry is never trusted."""
    monkeypatch.setattr(settings, "MEDIA_DIR", tmp_path)
    filename, _content_type, _size = media_store.save_upload(_valid_png(), uploaded_by=None)
    assert filename != "original.png"
    assert "/" not in filename and ".." not in filename


# -- Alt text is required before an image can be saved -----------------------


def test_inline_image_requires_alt_text(client_as):
    admin = models.get_user_by_email("admin@example.test")
    program = _seed_program(admin.id)
    c = client_as("editor")
    post = _create_draft_post(c, program.id)

    edit_page = c.get(f"/admin/posts/{post.id}/edit")
    token = _csrf_token_from(edit_page.text)
    response = c.post(
        f"/admin/posts/{post.id}/images",
        data={"alt_text": "   ", "csrf_token": token},
        files={"image": ("photo.jpg", _valid_jpeg(), "image/jpeg")},
    )
    assert "alt text is required" in response.text.lower()
    assert models.get_post_by_id(post.id).body == "x"


def test_cover_image_requires_alt_text(client_as):
    admin = models.get_user_by_email("admin@example.test")
    program = _seed_program(admin.id)
    c = client_as("editor")
    post = _create_draft_post(c, program.id)

    edit_page = c.get(f"/admin/posts/{post.id}/edit")
    token = _csrf_token_from(edit_page.text)
    response = c.post(
        f"/admin/posts/{post.id}/cover",
        data={"alt_text": "", "csrf_token": token},
        files={"image": ("cover.jpg", _valid_jpeg(), "image/jpeg")},
    )
    assert "alt text is required" in response.text.lower()
    assert models.get_post_by_id(post.id).cover_media_id is None


def test_invalid_upload_is_rejected_with_an_error_not_saved(client_as):
    admin = models.get_user_by_email("admin@example.test")
    program = _seed_program(admin.id)
    c = client_as("editor")
    post = _create_draft_post(c, program.id)

    edit_page = c.get(f"/admin/posts/{post.id}/edit")
    token = _csrf_token_from(edit_page.text)
    response = c.post(
        f"/admin/posts/{post.id}/images",
        data={"alt_text": "A photo", "csrf_token": token},
        files={"image": ("fake.jpg", _not_an_image(), "image/jpeg")},
    )
    assert response.status_code == 200
    assert "jpg, png, and webp" in response.text.lower()
    assert models.get_post_by_id(post.id).body == "x"
    assert models.list_all_pages()  # sanity: didn't blow up the fixture


# -- Inline images in a Post's body -------------------------------------------


def test_ambassador_adds_an_image_to_their_own_draft_post(client_as):
    admin = models.get_user_by_email("admin@example.test")
    program = _seed_program(admin.id)
    c = client_as("editor")
    post = _create_draft_post(c, program.id)

    edit_page = c.get(f"/admin/posts/{post.id}/edit")
    token = _csrf_token_from(edit_page.text)
    response = c.post(
        f"/admin/posts/{post.id}/images",
        data={"alt_text": "A view from the dorm", "csrf_token": token},
        files={"image": ("photo.jpg", _valid_jpeg(), "image/jpeg")},
        follow_redirects=False,
    )
    assert response.status_code == 303

    post = models.get_post_by_id(post.id)
    assert "![A view from the dorm](media/" in post.body


def test_ambassador_cannot_add_an_image_to_another_authors_post(client_as):
    admin = models.get_user_by_email("admin@example.test")
    program = _seed_program(admin.id)
    owner_post = models.create_post(
        program_id=program.id, title="Someone else's", body="x",
        topic="general", author_id=admin.id,
    )
    c = client_as("editor")
    token = _admin_csrf(c)
    response = c.post(
        f"/admin/posts/{owner_post.id}/images",
        data={"alt_text": "Not mine", "csrf_token": token},
        files={"image": ("photo.jpg", _valid_jpeg(), "image/jpeg")},
    )
    assert response.status_code == 403
    assert models.get_post_by_id(owner_post.id).body == "x"


def test_ambassador_cannot_add_an_image_once_their_post_is_submitted(client_as):
    """Same edit rule as the Post's text: only while draft."""
    admin = models.get_user_by_email("admin@example.test")
    program = _seed_program(admin.id)
    c = client_as("editor")
    post = _create_draft_post(c, program.id)
    token = _admin_csrf(c)
    c.post(f"/admin/posts/{post.id}/submit", data={"csrf_token": token})
    assert models.get_post_by_id(post.id).status == "pending"

    response = c.post(
        f"/admin/posts/{post.id}/images",
        data={"alt_text": "Too late", "csrf_token": token},
        files={"image": ("photo.jpg", _valid_jpeg(), "image/jpeg")},
    )
    assert response.status_code == 403
    assert models.get_post_by_id(post.id).body == "x"


def test_staff_can_add_an_image_to_any_post_regardless_of_status(client_as):
    editor = models.get_user_by_email("editor@example.test")
    program = _seed_program(editor.id)
    post = models.create_post(
        program_id=program.id, title="Theirs", body="x",
        topic="general", author_id=editor.id,
    )
    models.set_post_status(post.id, from_status="draft", to_status="pending")

    c = client_as("admin")
    token = _admin_csrf(c)
    response = c.post(
        f"/admin/posts/{post.id}/images",
        data={"alt_text": "Staff can add this", "csrf_token": token},
        files={"image": ("photo.jpg", _valid_jpeg(), "image/jpeg")},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "![Staff can add this](media/" in models.get_post_by_id(post.id).body


# -- Cover images: Post author vs. Program (Staff-only) ----------------------


def test_post_author_sets_their_own_posts_cover_image(client_as):
    admin = models.get_user_by_email("admin@example.test")
    program = _seed_program(admin.id)
    c = client_as("editor")
    post = _create_draft_post(c, program.id)

    edit_page = c.get(f"/admin/posts/{post.id}/edit")
    token = _csrf_token_from(edit_page.text)
    response = c.post(
        f"/admin/posts/{post.id}/cover",
        data={"alt_text": "Cover photo", "csrf_token": token},
        files={"image": ("cover.png", _valid_png(), "image/png")},
        follow_redirects=False,
    )
    assert response.status_code == 303
    post = models.get_post_by_id(post.id)
    assert post.cover_media_id is not None
    assert models.get_media_by_id(post.cover_media_id).alt_text == "Cover photo"


def test_ambassador_cannot_set_a_programs_cover_image(client_as):
    """Page routes are admin-only end to end — an Ambassador never even
    reaches the cover route for a Program (or any other Page)."""
    admin = models.get_user_by_email("admin@example.test")
    program = _seed_program(admin.id)
    c = client_as("editor")
    token = _admin_csrf(c)
    response = c.post(
        f"/admin/pages/{program.id}/cover",
        data={"alt_text": "Nice try", "csrf_token": token},
        files={"image": ("cover.png", _valid_png(), "image/png")},
    )
    assert response.status_code == 403
    assert models.get_page_by_id(program.id).cover_media_id is None


def test_staff_sets_a_programs_cover_image(client_as):
    admin = models.get_user_by_email("admin@example.test")
    program = _seed_program(admin.id)
    c = client_as("admin")
    token = _admin_csrf(c)
    response = c.post(
        f"/admin/pages/{program.id}/cover",
        data={"alt_text": "Program cover", "csrf_token": token},
        files={"image": ("cover.webp", _valid_webp(), "image/webp")},
        follow_redirects=False,
    )
    assert response.status_code == 303
    program = models.get_page_by_id(program.id)
    assert program.cover_media_id is not None


def test_cover_image_is_rejected_on_a_non_program_page(client_as):
    admin = models.get_user_by_email("admin@example.test")
    home = models.ensure_home_page()
    continent = models.publish_page(
        models.create_page(home.id, "Africa", "", False, admin.id).id
    )
    c = client_as("admin")
    token = _admin_csrf(c)
    response = c.post(
        f"/admin/pages/{continent.id}/cover",
        data={"alt_text": "Not a program", "csrf_token": token},
        files={"image": ("cover.png", _valid_png(), "image/png")},
    )
    assert response.status_code == 400
    assert models.get_page_by_id(continent.id).cover_media_id is None


# -- cms publish: only used-by-published Media is copied, with relative paths -


def test_published_posts_cover_and_inline_image_are_copied_and_linked(client_as, tmp_path):
    admin = models.get_user_by_email("admin@example.test")
    program = _seed_program(admin.id)
    c = client_as("admin")
    token = _admin_csrf(c)
    c.post(
        f"/admin/pages/{program.id}/cover",
        data={"alt_text": "Program cover", "csrf_token": token},
        files={"image": ("program.png", _valid_png(), "image/png")},
    )

    new_page = c.get(f"/admin/posts/new?program_id={program.id}")
    token = _csrf_token_from(new_page.text)
    c.post("/admin/posts/new", data={
        "program_id": str(program.id), "title": "Visa Day", "body": "Some text.",
        "topic": "other", "action": "save", "csrf_token": token,
    })
    post = models.list_posts_by_program(program.id)[0]
    edit_page = c.get(f"/admin/posts/{post.id}/edit")
    token = _csrf_token_from(edit_page.text)
    c.post(f"/admin/posts/{post.id}/cover",
           data={"alt_text": "Post cover", "csrf_token": token},
           files={"image": ("postcover.jpg", _valid_jpeg(), "image/jpeg")})
    c.post(f"/admin/posts/{post.id}/images",
           data={"alt_text": "Inline photo", "csrf_token": token},
           files={"image": ("inline.webp", _valid_webp(), "image/webp")})

    token = _admin_csrf(c)
    c.post(f"/admin/posts/{post.id}/publish", data={"csrf_token": token})
    assert models.get_post_by_id(post.id).status == "published"

    out = render_site(tmp_path / "site")
    media_files = list((out / "media").glob("*"))
    assert len(media_files) == 3  # program cover + post cover + inline image

    # The Program's cover shows on its own card, on its parent Country page
    # (two levels deep: site/asia/japan/index.html).
    country_html = (out / "asia" / "japan" / "index.html").read_text()
    assert 'class="card-cover" src="../../media/' in country_html
    assert 'alt="Program cover"' in country_html

    # The Post's cover shows on its card, on the Program page (three levels
    # deep) that lists it...
    program_html = (out / "asia" / "japan" / "kyoto-exchange" / "index.html").read_text()
    assert 'class="card-cover" src="../../../media/' in program_html
    assert 'alt="Post cover"' in program_html

    # ...and again, plus the inline image in its body, at the top of the
    # Post's own page (four levels deep).
    post_html = (
        out / "asia" / "japan" / "kyoto-exchange" / "visa-day" / "index.html"
    ).read_text()
    assert 'class="post-cover" src="../../../../media/' in post_html
    assert 'alt="Post cover"' in post_html
    assert 'src="../../../../media/' in post_html and 'alt="Inline photo"' in post_html


def test_a_drafts_images_are_never_published(client_as, tmp_path):
    admin = models.get_user_by_email("admin@example.test")
    program = _seed_program(admin.id)
    c = client_as("admin")

    new_page = c.get(f"/admin/posts/new?program_id={program.id}")
    token = _csrf_token_from(new_page.text)
    c.post("/admin/posts/new", data={
        "program_id": str(program.id), "title": "Still Drafting", "body": "Some text.",
        "topic": "other", "action": "save", "csrf_token": token,
    })
    post = models.list_posts_by_program(program.id)[0]
    assert post.status == "draft"

    edit_page = c.get(f"/admin/posts/{post.id}/edit")
    token = _csrf_token_from(edit_page.text)
    c.post(f"/admin/posts/{post.id}/cover",
           data={"alt_text": "Draft cover", "csrf_token": token},
           files={"image": ("draft.jpg", _valid_jpeg(), "image/jpeg")})
    c.post(f"/admin/posts/{post.id}/images",
           data={"alt_text": "Draft inline", "csrf_token": token},
           files={"image": ("draft2.png", _valid_png(), "image/png")})

    out = render_site(tmp_path / "site")
    assert not (out / "media").exists() or not list((out / "media").glob("*"))
    assert not list((out / "asia" / "japan" / "kyoto-exchange").glob("still-drafting"))


# -- Hand-typing another Post's (or a draft's) media id must never work ------


def test_hand_typed_media_id_from_another_post_is_not_resolved_or_published(
    client_as, tmp_path
):
    """A Post's body is a free-text form field — nothing stops a writer from
    typing `![x](media/<id>)` for an id that isn't theirs. It must never
    resolve to a real href, and app.publish must never copy that file."""
    admin = models.get_user_by_email("admin@example.test")
    program = _seed_program(admin.id)
    c = client_as("admin")

    other_post = models.create_post(
        program_id=program.id, title="Someone else's draft", body="x",
        topic="general", author_id=admin.id,
    )
    edit_page = c.get(f"/admin/posts/{other_post.id}/edit")
    token = _csrf_token_from(edit_page.text)
    c.post(f"/admin/posts/{other_post.id}/images",
           data={"alt_text": "Not yours", "csrf_token": token},
           files={"image": ("other.jpg", _valid_jpeg(), "image/jpeg")})

    # other_post.body is now "x\n\n![Not yours](media/<id>)\n" — read the id
    # back off the record rather than assuming it, same as the route does.
    other_post = models.get_post_by_id(other_post.id)
    other_media_id = max(markdown.referenced_media_ids(other_post.body))

    victim_post = models.create_post(
        program_id=program.id, title="Victim Post",
        body=f"Legit text.\n\n![stolen](media/{other_media_id})\n",
        topic="general", author_id=admin.id,
    )
    token = _admin_csrf(c)
    c.post(f"/admin/posts/{victim_post.id}/publish", data={"csrf_token": token})
    assert models.get_post_by_id(victim_post.id).status == "published"

    # Live preview never resolves the stolen id to a real href.
    live_html = c.get(f"/asia/japan/kyoto-exchange/victim-post/").text
    stolen_filename = models.get_media_by_id(other_media_id).filename
    assert stolen_filename not in live_html
    assert 'src="#"' in live_html  # the unresolved placeholder, not silently dropped

    out = render_site(tmp_path / "site")
    media_files = {p.name for p in (out / "media").glob("*")} if (out / "media").exists() else set()
    assert stolen_filename not in media_files

    victim_html = (
        out / "asia" / "japan" / "kyoto-exchange" / "victim-post" / "index.html"
    ).read_text()
    assert stolen_filename not in victim_html
    assert 'src="#"' in victim_html


def test_own_previously_uploaded_inline_image_still_renders_and_publishes(
    client_as, tmp_path
):
    """The ownership check must not break the sanctioned flow: an image this
    Post itself uploaded still resolves and gets copied."""
    admin = models.get_user_by_email("admin@example.test")
    program = _seed_program(admin.id)
    c = client_as("admin")

    new_page = c.get(f"/admin/posts/new?program_id={program.id}")
    token = _csrf_token_from(new_page.text)
    c.post("/admin/posts/new", data={
        "program_id": str(program.id), "title": "Legit Post", "body": "Some text.",
        "topic": "general", "action": "save", "csrf_token": token,
    })
    post = models.list_posts_by_program(program.id)[0]
    edit_page = c.get(f"/admin/posts/{post.id}/edit")
    token = _csrf_token_from(edit_page.text)
    c.post(f"/admin/posts/{post.id}/images",
           data={"alt_text": "Mine", "csrf_token": token},
           files={"image": ("mine.png", _valid_png(), "image/png")})

    token = _admin_csrf(c)
    c.post(f"/admin/posts/{post.id}/publish", data={"csrf_token": token})

    out = render_site(tmp_path / "site")
    media_files = list((out / "media").glob("*"))
    assert len(media_files) == 1
    post_html = (
        out / "asia" / "japan" / "kyoto-exchange" / "legit-post" / "index.html"
    ).read_text()
    assert f'src="../../../../media/{media_files[0].name}"' in post_html
    assert 'alt="Mine"' in post_html


# -- scripts/seed_demo.py: placeholder covers and inline images --------------


def test_seed_demo_seeds_program_covers_and_post_media(client):
    seed_demo = _load_seed_demo()
    admin = models.get_user_by_email("admin@example.test")
    editor = models.get_user_by_email("editor@example.test")
    programs = seed_demo._seed_pages(admin.id)
    seed_demo._seed_posts(programs, editor.id)

    assert programs
    for program in programs:
        program = models.get_page_by_id(program.id)
        assert program.cover_media_id is not None

    all_posts = [p for program in programs for p in models.list_posts_by_program(program.id)]
    with_cover = [p for p in all_posts if p.cover_media_id is not None]
    with_inline_image = [p for p in all_posts if "](media/" in p.body]
    assert with_cover
    assert with_inline_image
