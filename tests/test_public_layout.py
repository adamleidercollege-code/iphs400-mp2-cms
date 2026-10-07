"""T11 final design pass: the public layout contract.

Covers the things a screenshot would catch but a unit test otherwise would
not — the preview and the export sharing one stylesheet, pages having their
supporting sections, and the demo catalog reading like real student writing.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

from app import models, publish
from app.publish import render_site
from app.services import markdown

_ROOT = Path(__file__).resolve().parents[1]


def _load_seed_demo():
    spec = importlib.util.spec_from_file_location(
        "seed_demo", _ROOT / "scripts" / "seed_demo.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _seed(client_unused=None):
    seed_demo = _load_seed_demo()
    admin = models.get_user_by_email("admin@example.test")
    editor = models.get_user_by_email("editor@example.test")
    programs = seed_demo._seed_pages(admin.id)
    seed_demo._seed_posts(programs, editor.id)
    return seed_demo, programs


# --- the preview and the export must agree -----------------------------------


def test_preview_stylesheet_is_not_html_escaped(client):
    """The live preview inlines the stylesheet in a <style> block. Jinja's
    HTML autoescaping would turn a child combinator into "&gt;" and silently
    drop those rules, so the preview would stop matching the exported site."""
    _seed()
    style = client.get("/").text.split("<style>")[1].split("</style>")[0]

    assert "&gt;" not in style
    assert ".card-grid > .card:only-child" in style
    assert style == publish.CSS


def test_exported_stylesheet_link_is_cache_busted(client, tmp_path):
    """GitHub Pages caches style.css, so a redesign has to arrive under a new
    URL or returning readers keep the old one."""
    _seed()
    out = render_site(tmp_path / "site")

    home = (out / "index.html").read_text()
    assert f'href="style.css?v={publish.CSS_VERSION}"' in home
    nested = (out / "asia" / "japan" / "index.html").read_text()
    assert f'href="../../style.css?v={publish.CSS_VERSION}"' in nested
    assert (out / "style.css").exists()


# --- every page type carries its supporting sections -------------------------


def test_home_leads_with_a_featured_dispatch_and_lists_the_latest(client, tmp_path):
    _seed()
    out = render_site(tmp_path / "site")
    home = (out / "index.html").read_text()

    assert "Featured dispatch" in home
    assert "Explore by region" in home
    assert "Latest dispatches" in home
    newest = models.list_recent_published_posts(1)[0]
    assert newest.title in home


def test_continent_and_country_pages_end_with_recent_dispatches(client, tmp_path):
    _seed()
    out = render_site(tmp_path / "site")

    assert "Recent dispatches from Asia" in (out / "asia" / "index.html").read_text()
    japan = (out / "asia" / "japan" / "index.html").read_text()
    assert "Recent dispatches from Japan" in japan
    assert "Programs in Japan" in japan


def test_standalone_pages_render_sections_as_cards_plus_a_way_onward(client, tmp_path):
    """About CGE and Contact Us keep a compact tinted header and move their
    body into cards, so neither ends in an empty white page."""
    _seed()
    out = render_site(tmp_path / "site")

    about = (out / "about-cge" / "index.html").read_text()
    for heading in ["Advising", "Pre-departure and re-entry", "Student ambassadors"]:
        assert f'class="info-card-title">{heading}<' in about
    assert "Latest dispatches" in about

    contact = (out / "contact-us" / "index.html").read_text()
    for heading in ["Email", "Office", "Hours"]:
        assert f'class="info-card-title">{heading}<' in contact
    assert "cge-demo@kenyon.edu" in contact
    assert "Latest dispatches" in contact


def test_post_pages_have_an_author_row_a_back_button_and_more_from(client, tmp_path):
    _seed()
    out = render_site(tmp_path / "site")
    post_dir = out / "africa" / "kenya" / "nairobi-fieldwork"
    post = (post_dir / "fieldwork-notes-are-not-essays" / "index.html").read_text()

    assert 'class="byline-name"' in post
    assert "Ambassador &middot; Nairobi Fieldwork" in post or "Ambassador · Nairobi Fieldwork" in post
    assert 'class="btn"' in post and "Back to Nairobi Fieldwork" in post
    assert "More from Nairobi Fieldwork" in post


def test_every_public_page_puts_its_breadcrumb_trail_above_the_title(client, tmp_path):
    """Except Home, which has nowhere to go up to."""
    _seed()
    out = render_site(tmp_path / "site")

    assert 'class="breadcrumb"' not in (out / "index.html").read_text()
    for path in [
        ("asia", "index.html"),
        ("asia", "japan", "index.html"),
        ("about-cge", "index.html"),
        ("africa", "kenya", "nairobi-fieldwork", "fieldwork-notes-are-not-essays",
         "index.html"),
    ]:
        html = out.joinpath(*path).read_text()
        assert 'class="breadcrumb"' in html, path
        assert 'class="breadcrumb-current"' in html, path


# --- the demo catalog --------------------------------------------------------


def test_public_bylines_never_show_a_demo_account_label(client, tmp_path):
    """Seeded accounts are named like students, because their names are the
    bylines readers see."""
    _seed()
    out = render_site(tmp_path / "site")

    for html_file in out.rglob("index.html"):
        text = html_file.read_text()
        assert "Ambassador Demo" not in text, html_file
        assert "Staff Demo" not in text, html_file

    assert "Maya Chen" in (out / "asia" / "japan" / "kyoto-exchange" / "index.html").read_text()


def test_seeded_dispatches_have_distinct_titles_and_spread_out_dates(client):
    _seed_demo, programs = _seed()
    posts = [p for program in programs for p in models.list_posts_by_program(program.id)]

    titles = [p.title for p in posts]
    assert len(set(titles)) == len(titles)
    assert not any(title.startswith("My first week at") for title in titles)

    published_dates = {p.published_at[:10] for p in posts if p.status == "published"}
    assert len(published_dates) > 5


def test_seeded_dispatches_have_real_substance(client):
    """Each body carries a subheading and a pull quote, so a Post page has
    something to typeset."""
    _seed_demo, programs = _seed()
    posts = [p for program in programs for p in models.list_posts_by_program(program.id)]

    assert len(posts) == len(programs) * 3
    for post in posts:
        assert "\n## " in post.body, post.title
        assert "\n> " in post.body, post.title
        assert len(post.body.split("\n\n")) >= 4, post.title


# --- the Markdown helpers the layout depends on ------------------------------


def test_split_intro_separates_the_opening_paragraph():
    intro, rest = markdown.split_intro("First para.\n\nSecond para.\n\nThird.")
    assert intro == "First para."
    assert rest == "Second para.\n\nThird."

    assert markdown.split_intro("Only one.") == ("Only one.", "")
    assert markdown.split_intro("") == ("", "")
    # A body that opens with a section has no intro to lift out.
    assert markdown.split_intro("## Heading\n\nBody.") == ("", "## Heading\n\nBody.")


def test_split_sections_turns_h2_blocks_into_cards():
    body = "Intro.\n\n## First\n\nOne.\n\n## Second\n\nTwo.\n"
    assert markdown.split_sections(body) == [("First", "One."), ("Second", "Two.")]
    assert markdown.strip_sections(body) == "Intro."
    assert markdown.split_sections("No headings here.") == []
