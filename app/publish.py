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

CSS = """/* Kenyon purple plus a warm gold accent; editorial travel-blog pass, T11. */
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
  --topic-general: #5B2A86;
  --topic-housing: #2E7D6B;
  --topic-meals: #C9573B;
  --topic-social-life: #B0538B;
  --topic-academics: #2E6CA8;
  --topic-other: #6B6356;
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
  position: sticky;
  top: 0;
  z-index: 10;
  background: rgba(91, 42, 134, 0.85);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  padding: 1rem 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.12);
}
.site-nav {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem 1.5rem;
}
.site-nav a {
  color: #E7D9F2;
  font-weight: 600;
  text-decoration: none;
  padding-bottom: 0.2rem;
  border-bottom: 2px solid transparent;
}
.site-nav a:hover { color: #fff; }
.site-nav a.is-active { color: #fff; border-bottom-color: var(--gold); }

.breadcrumb {
  font-size: 0.9rem;
  margin-block: 1rem;
  color: var(--muted);
}
.breadcrumb a { color: inherit; }

main { display: block; padding-bottom: 2rem; }

/* -- hero (Home only) ----------------------------------------------- */
.hero {
  position: relative;
  overflow: hidden;
  background: linear-gradient(135deg, var(--purple) 0%, var(--purple-dark) 60%, #2A1240 100%);
  color: #fff;
  padding: 5rem 0 4.5rem;
  margin-bottom: 2.5rem;
}
.hero::before, .hero::after {
  content: "";
  position: absolute;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(201, 138, 59, 0.35), transparent 70%);
  pointer-events: none;
}
.hero::before { width: 26rem; height: 26rem; top: -10rem; right: -6rem; }
.hero::after {
  width: 18rem;
  height: 18rem;
  left: -6rem;
  bottom: -9rem;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.12), transparent 70%);
}
.hero .wrap { position: relative; }
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
.hero-cta {
  display: inline-block;
  margin-top: 1.75rem;
  background: var(--gold);
  color: #2A1240;
  font-weight: 600;
  text-decoration: none;
  padding: 0.75rem 1.5rem;
  border-radius: 999px;
  transition: transform 0.15s ease, background 0.15s ease;
}
.hero-cta:hover { background: #E0A861; transform: translateY(-1px); }

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
  position: relative;
  border: 1px solid var(--card-border);
  border-top: 4px solid var(--gold);
  border-radius: 0.75rem;
  padding: 1.5rem 1.5rem 1.25rem;
  background: var(--purple-light);
  transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
}
.card:hover {
  transform: translateY(-4px);
  border-color: var(--gold);
  box-shadow: 0 12px 24px -10px rgba(31, 22, 38, 0.35);
}
.card a {
  text-decoration: none;
  font-weight: 600;
  font-family: "Fraunces", Georgia, serif;
  font-size: 1.15rem;
}
.card a:hover { color: var(--gold-dark); }
.card-flag { margin-right: 0.4rem; }
.card-desc {
  font-size: 0.92rem;
  color: var(--muted);
  margin: 0.5rem 0 0;
}
.post-meta { font-size: 0.85rem; color: var(--muted); margin: 0.35rem 0 0; }
.post-topic-badge {
  display: inline-block;
  flex-shrink: 0;
  white-space: nowrap;
  background: var(--topic-general);
  color: #fff;
  border-radius: 999px;
  padding: 0.2rem 0.85rem;
  font-size: 0.8rem;
  font-weight: 600;
}
.post-topic-badge.topic-general { background: var(--topic-general); }
.post-topic-badge.topic-housing { background: var(--topic-housing); }
.post-topic-badge.topic-meals { background: var(--topic-meals); }
.post-topic-badge.topic-social-life { background: var(--topic-social-life); }
.post-topic-badge.topic-academics { background: var(--topic-academics); }
.post-topic-badge.topic-other { background: var(--topic-other); }

.post-card { display: flex; flex-direction: column; gap: 0.6rem; }
.post-card-top { display: flex; flex-wrap: wrap; align-items: flex-start; justify-content: space-between; gap: 0.5rem 0.75rem; }
.post-avatar {
  flex-shrink: 0;
  width: 2.25rem;
  height: 2.25rem;
  border-radius: 50%;
  background: var(--purple);
  color: #fff;
  font-size: 0.8rem;
  font-weight: 700;
  font-family: "Inter", system-ui, sans-serif;
  display: flex;
  align-items: center;
  justify-content: center;
}
.post-card-byline {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  margin-top: 0.25rem;
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
.topic-pill[data-topic="housing"] { border-color: var(--topic-housing); color: var(--topic-housing); }
.topic-pill[data-topic="housing"].is-active { background: var(--topic-housing); color: #fff; }
.topic-pill[data-topic="meals"] { border-color: var(--topic-meals); color: var(--topic-meals); }
.topic-pill[data-topic="meals"].is-active { background: var(--topic-meals); color: #fff; }
.topic-pill[data-topic="social-life"] { border-color: var(--topic-social-life); color: var(--topic-social-life); }
.topic-pill[data-topic="social-life"].is-active { background: var(--topic-social-life); color: #fff; }
.topic-pill[data-topic="academics"] { border-color: var(--topic-academics); color: var(--topic-academics); }
.topic-pill[data-topic="academics"].is-active { background: var(--topic-academics); color: #fff; }
.topic-pill[data-topic="other"] { border-color: var(--topic-other); color: var(--topic-other); }
.topic-pill[data-topic="other"].is-active { background: var(--topic-other); color: #fff; }

.post-topic-group h2 { margin-top: 2.5rem; }

/* -- a single post --------------------------------------------------- */
.post {
  max-width: 42rem;
  margin: 0 auto;
}
.post h1 { margin-top: 0.75rem; font-size: clamp(2rem, 4.5vw, 2.75rem); }
.post h2 { margin-top: 2rem; }
.post blockquote {
  margin: 1.5rem 0;
  padding: 0.25rem 1.25rem;
  border-left: 3px solid var(--gold);
  color: var(--muted);
  font-style: italic;
}
.post ul, .post ol { padding-left: 1.5rem; }
.post li { margin: 0.35rem 0; }
.post-back { margin-top: 2.5rem; }

/* -- footer ----------------------------------------------------------- */
.site-footer {
  background: var(--purple-dark);
  color: #D9CBE8;
  margin-top: 2rem;
  padding: 2.5rem 0 1.5rem;
}
.footer-grid {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 1.5rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.12);
  padding-bottom: 1.5rem;
  margin-bottom: 1rem;
}
.footer-brand h2 {
  color: #fff;
  font-size: 1.3rem;
  margin: 0 0 0.35rem;
}
.footer-brand p { max-width: 28rem; margin: 0; color: #C7B4D8; }
.site-footer-nav {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem 1.5rem;
  align-content: flex-start;
}
.site-footer-nav a { color: #fff; text-decoration: none; }
.site-footer-nav a:hover { color: var(--gold); }
.footer-note { color: #B6A3C7; }

@media (max-width: 480px) {
  .site-nav, .site-footer-nav { flex-direction: column; gap: 0.5rem; }
  .card-grid { grid-template-columns: 1fr; }
  .hero { padding: 3rem 0; }
  .wrap { padding: 0 1rem; }
  .post-card-top { flex-direction: column; }
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
    active_id: int,
) -> tuple[str, list[dict], list[dict]]:
    """CSS path, nav, and footer links for the page/post living at `chain` —
    shared between a Page's own render and each of its Posts' renders."""
    css_path = _relative_link(chain, [])[: -len("index.html")] + "style.css"
    nav = [
        {"title": home.title, "href": _relative_link(chain, []), "active": active_id == home.id}
    ] + [
        {
            "title": c.title,
            "href": _relative_link(chain, chains[c.id]),
            "active": active_id == c.id,
        }
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
        active_id = models.nav_root_id(page, home)
        css_path, nav, footer_links = _furniture(
            chain, home, continents, footer_pages, chains, active_id
        )
        breadcrumb = [
            {"title": a.title, "href": _relative_link(chain, chains[a.id])}
            for a in models.list_ancestors(page)
        ] + [{"title": page.title, "href": _relative_link(chain, chain)}]
        show_flag = models.is_continent_page(page)
        children = [
            post_view.page_card(c, _relative_link(chain, chains[c.id]), show_flag)
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
                    post_chain, home, continents, footer_pages, chains, active_id
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
