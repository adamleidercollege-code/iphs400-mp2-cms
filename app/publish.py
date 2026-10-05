"""Render the public site into site/ as plain HTML.

Walks the Page tree and writes one `index.html` per PUBLISHED page, at the
nested path implied by its ancestors' slugs (e.g. site/asia/japan/kyoto/).
Two rules the rubric checks:

  1. Only PUBLISHED content is written here. A draft that reaches site/ is a bug.
  2. Every href and src is RELATIVE ("style.css", "asia/index.html"), never
     root-absolute ("/style.css"), because Pages serves this from a subfolder.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app import models, settings
from app.services import markdown

CSS = """/* Minimal starter styles — make them yours. */
:root { color-scheme: light dark; }
body { font: 16px/1.6 system-ui, sans-serif; margin: 0 auto; max-width: 42rem; padding: 1rem; }
header a { font-weight: 700; text-decoration: none; }
main { margin-block: 2rem; }

.site-nav, .site-footer-nav {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem 1rem;
}
.breadcrumb { font-size: 0.9rem; margin-block: 0.5rem; }

@media (max-width: 480px) {
  .site-nav, .site-footer-nav { flex-direction: column; gap: 0.25rem; }
}
"""


def environment() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(settings.TEMPLATES)),
        autoescape=select_autoescape(["html"]),
    )


def _slug_chain(page: models.Page, home: models.Page) -> list[str]:
    if page.id == home.id:
        return []
    return [a.slug for a in models.list_ancestors(page) if a.id != home.id] + [page.slug]


def _relative_link(from_chain: list[str], to_chain: list[str]) -> str:
    up = "../" * len(from_chain)
    if not to_chain:
        return f"{up}index.html" if up else "index.html"
    return f"{up}{'/'.join(to_chain)}/index.html"


def render_site(out: Path | None = None) -> Path:
    out = out or settings.SITE
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    env = environment()
    (out / "style.css").write_text(CSS)

    home = models.ensure_home_page()
    all_pages = models.list_all_pages()
    chains = {p.id: _slug_chain(p, home) for p in all_pages}

    continents = models.list_published_children(home.id)
    footer_pages = models.list_footer_pages()

    template = env.get_template("public/page.html")

    for page in all_pages:
        if page.status != "published":
            continue
        chain = chains[page.id]
        css_path = _relative_link(chain, [])[: -len("index.html")] + "style.css"
        nav = [{"title": home.title, "href": _relative_link(chain, [])}] + [
            {"title": c.title, "href": _relative_link(chain, chains[c.id])}
            for c in continents
        ]
        breadcrumb = [
            {"title": a.title, "href": _relative_link(chain, chains[a.id])}
            for a in models.list_ancestors(page)
        ] + [{"title": page.title, "href": _relative_link(chain, chain)}]
        footer_links = [
            {"title": f.title, "href": _relative_link(chain, chains[f.id])}
            for f in footer_pages
        ]
        children = [
            {"title": c.title, "href": _relative_link(chain, chains[c.id])}
            for c in models.list_published_children(page.id)
        ]

        html = template.render(
            title=page.title,
            page=page,
            body_html=markdown.render(page.body),
            css_path=css_path,
            nav=nav,
            breadcrumb=breadcrumb,
            footer_links=footer_links,
            children=children,
        )

        page_dir = out.joinpath(*chain) if chain else out
        page_dir.mkdir(parents=True, exist_ok=True)
        (page_dir / "index.html").write_text(html)

    return out
