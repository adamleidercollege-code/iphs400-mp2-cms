"""T11 follow-up: crawl the exported site/ and fail on any broken internal
link — the bug that shipped was "About CGE"/"Contact Us" footer links going
nowhere, which a human skim of the templates didn't catch."""
from __future__ import annotations

import importlib.util
import re
from pathlib import Path

from app import models
from app.publish import render_site

_ROOT = Path(__file__).resolve().parents[1]

_LINK_RE = re.compile(r'(?:href|src)="([^"]+)"')


def _load_seed_demo():
    spec = importlib.util.spec_from_file_location(
        "seed_demo", _ROOT / "scripts" / "seed_demo.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_exported_site_has_no_broken_internal_links(client, tmp_path):
    seed_demo = _load_seed_demo()
    admin = models.get_user_by_email("admin@example.test")
    editor = models.get_user_by_email("editor@example.test")
    programs = seed_demo._seed_pages(admin.id)
    seed_demo._seed_posts(programs, editor.id)

    out = render_site(tmp_path / "site")
    html_files = list(out.rglob("index.html"))
    assert html_files, "render_site produced no pages to crawl"

    broken: list[str] = []
    for html_file in html_files:
        html = html_file.read_text()
        for link in _LINK_RE.findall(html):
            if link.startswith(("http://", "https://", "mailto:", "#", "data:")):
                continue
            target = (html_file.parent / link).resolve()
            if not target.exists():
                broken.append(f"{html_file.relative_to(out)} -> {link}")

    assert not broken, "broken internal link(s):\n" + "\n".join(broken)


def test_footer_pages_are_published_with_real_content_and_resolve(client, tmp_path):
    """The specific regression: About CGE and Contact Us must be seeded as
    published standalone Pages with real (non-placeholder) bodies, and their
    footer links must resolve to an actual exported page."""
    seed_demo = _load_seed_demo()
    admin = models.get_user_by_email("admin@example.test")
    editor = models.get_user_by_email("editor@example.test")
    programs = seed_demo._seed_pages(admin.id)
    seed_demo._seed_posts(programs, editor.id)

    for title, slug in [("About CGE", "about-cge"), ("Contact Us", "contact-us")]:
        page = models.get_child_by_slug(models.ensure_home_page().id, slug)
        assert page is not None, f"{title} was not seeded"
        assert page.status == "published"
        assert page.show_in_footer is True
        assert "Placeholder copy" not in page.body
        assert len(page.body) > 40

    out = render_site(tmp_path / "site")
    home_html = (out / "index.html").read_text()
    assert 'href="about-cge/index.html"' in home_html
    assert 'href="contact-us/index.html"' in home_html
    assert (out / "about-cge" / "index.html").exists()
    assert (out / "contact-us" / "index.html").exists()

    contact_html = (out / "contact-us" / "index.html").read_text()
    assert "cge-demo@kenyon.edu" in contact_html
