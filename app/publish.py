"""Render the public site into site/ as plain HTML.

Walks the Page tree and writes one `index.html` per PUBLISHED page, at the
nested path implied by its ancestors' slugs (e.g. site/asia/japan/kyoto/),
plus one `index.html` per PUBLISHED Post, nested one level under its Program
(e.g. site/asia/japan/kyoto/my-first-week/). Two rules the rubric checks:

  1. Only PUBLISHED content is written here. A draft or pending Post, like a
     draft Page, reaching site/ is a bug.
  2. Every href and src is RELATIVE ("style.css", "asia/index.html"), never
     root-absolute ("/style.css"), because Pages serves this from a subfolder.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app import models, settings
from app.services import markdown, post_view

CSS = """/* Kenyon purple plus a warm gold accent, per the T10 design pass. */
:root {
  color-scheme: light dark;
  --purple: #5B2A86;
  --purple-dark: #3E1C5E;
  --purple-light: #F2EBFA;
  --gold: #C98A3B;
  --gold-dark: #9C6723;
  --ink: #1F1626;
  --muted: #5a5064;
  --card-border: #DCCFEA;
  --paper: #FDFBFE;
}
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body {
  font: 16px/1.65 "Inter", system-ui, sans-serif;
  margin: 0;
  padding: 0;
  color: var(--ink);
  background: var(--paper);
  overflow-x: hidden;
  overflow-wrap: anywhere;
}
h1, h2, h3 { font-family: "Fraunces", Georgia, serif; line-height: 1.2; }
a { color: var(--purple-dark); }
.wrap {
  max-width: 72rem;
  margin: 0 auto;
  padding: 0 1.25rem;
}

/* -- header / nav -------------------------------------------------- */
.site-header {
  background: var(--purple);
  padding: 1rem 0;
}
.site-nav {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem 1.5rem;
}
.site-nav a { color: #fff; font-weight: 600; text-decoration: none; }
.site-nav a:hover { color: var(--gold); text-decoration: none; }

.breadcrumb {
  font-size: 0.9rem;
  margin-block: 1rem;
  color: var(--muted);
}
.breadcrumb a { color: inherit; }

main { display: block; padding-bottom: 2rem; }

/* -- hero (Home only) ----------------------------------------------- */
.hero {
  background: linear-gradient(135deg, var(--purple) 0%, var(--purple-dark) 100%);
  color: #fff;
  padding: 4rem 0 3.5rem;
  margin-bottom: 2.5rem;
}
.hero h1 {
  font-size: clamp(2.25rem, 5vw, 3.5rem);
  margin: 0 0 1rem;
}
.hero-body {
  max-width: 42rem;
  font-size: 1.15rem;
  color: #EDE3F7;
}
.hero-body :first-child { margin-top: 0; }

.page-title {
  font-size: clamp(1.75rem, 4vw, 2.5rem);
  margin: 2rem 0 1rem;
}

/* -- card grids: Continents, Countries, Programs -------------------- */
.card-grid {
  list-style: none;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(15rem, 1fr));
  gap: 1.25rem;
  margin: 1.5rem 0;
  padding: 0;
}
.card {
  border: 1px solid var(--card-border);
  border-radius: 0.75rem;
  padding: 1.25rem 1.5rem;
  background: var(--purple-light);
  transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
}
.card:hover {
  transform: translateY(-2px);
  border-color: var(--gold);
  box-shadow: 0 8px 20px -10px rgba(31, 22, 38, 0.35);
}
.card a {
  text-decoration: none;
  font-weight: 600;
  font-family: "Fraunces", Georgia, serif;
  font-size: 1.1rem;
}
.card a:hover { color: var(--gold-dark); }
.post-meta { font-size: 0.85rem; color: var(--muted); margin: 0.35rem 0 0; }
.post-topic-badge {
  display: inline-block;
  background: var(--gold);
  color: #fff;
  border-radius: 999px;
  padding: 0.2rem 0.85rem;
  font-size: 0.8rem;
  font-weight: 600;
}

.topic-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin: 1.5rem 0;
}
.topic-pill {
  border: 1px solid var(--purple);
  background: #fff;
  color: var(--purple-dark);
  border-radius: 999px;
  padding: 0.35rem 0.9rem;
  font: inherit;
  cursor: pointer;
}
.topic-pill.is-active { background: var(--purple); color: #fff; border-color: var(--purple); }

.post-topic-group h2 { margin-top: 2.5rem; }

/* -- a single post --------------------------------------------------- */
.post h1 { margin-top: 0.75rem; }
.post-back { margin-top: 2.5rem; }

/* -- footer ----------------------------------------------------------- */
.site-footer {
  background: var(--purple-dark);
  color: #D9CBE8;
  margin-top: 2rem;
  padding: 2rem 0 1.5rem;
}
.site-footer-nav {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem 1.5rem;
  margin-bottom: 1rem;
}
.site-footer-nav a { color: #fff; text-decoration: none; }
.site-footer-nav a:hover { color: var(--gold); }
.footer-note { color: #B6A3C7; }

@media (max-width: 480px) {
  .site-nav, .site-footer-nav { flex-direction: column; gap: 0.5rem; }
  .card-grid { grid-template-columns: 1fr; }
  .hero { padding: 2.5rem 0; }
  .wrap { padding: 0 1rem; }
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


def _furniture(
    chain: list[str],
    home: models.Page,
    continents: list[models.Page],
    footer_pages: list[models.Page],
    chains: dict[int, list[str]],
) -> tuple[str, list[dict], list[dict]]:
    """CSS path, nav, and footer links for the page/post living at `chain` —
    shared between a Page's own render and each of its Posts' renders."""
    css_path = _relative_link(chain, [])[: -len("index.html")] + "style.css"
    nav = [{"title": home.title, "href": _relative_link(chain, [])}] + [
        {"title": c.title, "href": _relative_link(chain, chains[c.id])}
        for c in continents
    ]
    footer_links = [
        {"title": f.title, "href": _relative_link(chain, chains[f.id])}
        for f in footer_pages
    ]
    return css_path, nav, footer_links


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

    page_template = env.get_template("public/page.html")
    post_template = env.get_template("public/post.html")

    for page in all_pages:
        if page.status != "published":
            continue
        chain = chains[page.id]
        css_path, nav, footer_links = _furniture(chain, home, continents, footer_pages, chains)
        breadcrumb = [
            {"title": a.title, "href": _relative_link(chain, chains[a.id])}
            for a in models.list_ancestors(page)
        ] + [{"title": page.title, "href": _relative_link(chain, chain)}]
        children = [
            {"title": c.title, "href": _relative_link(chain, chains[c.id])}
            for c in models.list_published_children(page.id)
        ]

        post_groups = None
        if models.is_program_page(page):
            posts = models.list_published_posts_by_program(page.id)
            post_groups = post_view.grouped_post_summaries(
                posts, lambda post: _relative_link(chain, chain + [post.slug])
            )

        html = page_template.render(
            title=page.title,
            page=page,
            body_html=markdown.render(page.body),
            css_path=css_path,
            nav=nav,
            breadcrumb=breadcrumb,
            footer_links=footer_links,
            children=children,
            post_groups=post_groups,
        )

        page_dir = out.joinpath(*chain) if chain else out
        page_dir.mkdir(parents=True, exist_ok=True)
        (page_dir / "index.html").write_text(html)

        if not post_groups:
            continue
        for _topic_value, _topic_label, summaries in post_groups:
            for summary in summaries:
                post = summary["post"]
                post_chain = chain + [post.slug]
                post_css_path, post_nav, post_footer_links = _furniture(
                    post_chain, home, continents, footer_pages, chains
                )
                post_breadcrumb = [
                    {"title": a.title, "href": _relative_link(post_chain, chains[a.id])}
                    for a in models.list_ancestors(page)
                ] + [
                    {"title": page.title, "href": _relative_link(post_chain, chain)},
                    {"title": post.title, "href": _relative_link(post_chain, post_chain)},
                ]
                post_html = post_template.render(
                    title=post.title,
                    post=post,
                    topic_label=summary["topic_label"],
                    author_name=summary["author_name"],
                    published_date=summary["published_date"],
                    body_html=markdown.render(post.body),
                    css_path=post_css_path,
                    nav=post_nav,
                    breadcrumb=post_breadcrumb,
                    footer_links=post_footer_links,
                    program_href=_relative_link(post_chain, chain),
                    program_title=page.title,
                )
                post_dir = out.joinpath(*post_chain)
                post_dir.mkdir(parents=True, exist_ok=True)
                (post_dir / "index.html").write_text(post_html)

    return out
