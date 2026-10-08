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

import hashlib
import json
import shutil
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app import models, settings
from app.services import markdown, post_view, search_index

CSS = """/* Kenyon purple plus a warm gold accent; editorial travel-magazine pass, T11.
   Layout rule this pass enforces: prose always sits in a container (a tinted
   band, a panel, or a card) and every section announces itself, so no page
   ends in an unstructured white gap. */
:root {
  color-scheme: light dark;
  --purple: #5B2A86;
  --purple-dark: #3E1C5E;
  --purple-light: #F2EBFA;
  --gold: #C98A3B;
  --gold-dark: #9C6723;
  --ink: #1F1626;
  --muted: #5a5064;
  --card-border: #E4DCEC;
  --paper: #FDFBFE;
  --panel: #FFFFFF;
  --section-gap: 3.5rem;
  --topic-general: #5B2A86;
  --topic-housing: #2E7D6B;
  --topic-meals: #C9573B;
  --topic-social-life: #B0538B;
  --topic-academics: #2E6CA8;
  --topic-other: #6B6356;
  /* Region accents: one per Continent (cycles if a 7th is added), used for
     card top-accents and the interior page-header band. */
  --region-0: #C98A3B; --region-0-tint: #FBF0DF;
  --region-1: #2E7D6B; --region-1-tint: #E3F3EF;
  --region-2: #C9573B; --region-2-tint: #FBE9E4;
  --region-3: #2E6CA8; --region-3-tint: #E4EEF8;
  --region-4: #B0538B; --region-4-tint: #FAE9F3;
  --region-5: #6B6356; --region-5-tint: #F1EEE9;
}
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body {
  font: 16px/1.65 "Inter", system-ui, sans-serif;
  margin: 0;
  padding: 0;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  color: var(--ink);
  background: var(--paper);
  overflow-x: hidden;
  overflow-wrap: anywhere;
}
h1, h2, h3 { font-family: "Fraunces", Georgia, serif; line-height: 1.2; }
a { color: var(--purple-dark); }
:focus-visible {
  outline: 3px solid var(--gold);
  outline-offset: 2px;
  border-radius: 2px;
}
.wrap {
  max-width: 72rem;
  margin: 0 auto;
  padding: 0 1.25rem;
}
main { display: block; flex: 1 0 auto; padding-bottom: var(--section-gap); }

/* -- header / nav -------------------------------------------------- */
.site-header {
  position: sticky;
  top: 0;
  z-index: 10;
  flex-shrink: 0;
  background: rgba(91, 42, 134, 0.92);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  padding: 1rem 0;
  box-shadow: 0 1px 0 rgba(0, 0, 0, 0.08);
}
.header-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 0.6rem 1.5rem;
}
.wordmark {
  color: #fff;
  font-family: "Fraunces", Georgia, serif;
  font-weight: 600;
  font-size: 1.15rem;
  text-decoration: none;
  letter-spacing: 0.01em;
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

/* -- breadcrumb ------------------------------------------------------ */
.breadcrumb {
  font-size: 0.95rem;
  margin: 0 0 1.25rem;
  color: var(--muted);
}
.breadcrumb a {
  color: var(--purple);
  font-weight: 500;
  text-decoration: none;
}
.breadcrumb a:hover { text-decoration: underline; }
.breadcrumb-sep { margin: 0 0.45rem; color: var(--muted); opacity: 0.7; }
.breadcrumb-current { color: var(--ink); font-weight: 700; }

/* -- hero (Home only) ----------------------------------------------- */
.hero {
  position: relative;
  overflow: hidden;
  background: linear-gradient(135deg, var(--purple) 0%, var(--purple-dark) 100%);
  color: #fff;
  padding: 3.5rem 0;
}
.hero::before {
  content: "";
  position: absolute;
  inset: 0;
  background-image:
    repeating-linear-gradient(135deg, rgba(255, 255, 255, 0.04) 0 2px, transparent 2px 28px);
  pointer-events: none;
}
/* A single balanced column — narrower than .wrap so a short headline and
   pitch don't stretch edge-to-edge once there's no second column beside them. */
.hero-inner {
  position: relative;
  max-width: 36rem;
  margin: 0 auto;
  text-align: center;
}
.hero h1 {
  font-size: clamp(2.1rem, 4.2vw, 2.85rem);
  margin: 0 0 1rem;
}
.hero-body {
  font-size: 1.1rem;
  color: #EDE3F7;
  margin: 0 auto;
}
.hero-cta {
  display: inline-block;
  margin-top: 1.6rem;
  background: var(--gold);
  color: #2A1240;
  font-weight: 600;
  text-decoration: none;
  padding: 0.75rem 1.5rem;
  border-radius: 999px;
  transition: transform 0.15s ease, background 0.15s ease;
}
.hero-cta:hover { background: #E0A861; transform: translateY(-1px); }

/* -- interior page-header band --------------------------------------- */
.page-header {
  background: var(--purple-light);
  padding: 2.25rem 0 2rem;
  border-bottom: 3px solid var(--gold);
}
.page-title { font-size: clamp(1.75rem, 4vw, 2.5rem); margin: 0 0 0.5rem; }
.page-desc { max-width: 42rem; color: var(--muted); }
.page-desc :first-child { margin-top: 0; }
.page-desc :last-child { margin-bottom: 0; }
.page-header.region-0 { background: var(--region-0-tint); border-bottom-color: var(--region-0); }
.page-header.region-1 { background: var(--region-1-tint); border-bottom-color: var(--region-1); }
.page-header.region-2 { background: var(--region-2-tint); border-bottom-color: var(--region-2); }
.page-header.region-3 { background: var(--region-3-tint); border-bottom-color: var(--region-3); }
.page-header.region-4 { background: var(--region-4-tint); border-bottom-color: var(--region-4); }
.page-header.region-5 { background: var(--region-5-tint); border-bottom-color: var(--region-5); }

/* -- sections and panels --------------------------------------------- */
.section { margin-top: var(--section-gap); }
.section-title {
  font-size: 1.6rem;
  margin: 0 0 1.5rem;
}
.section-title::after {
  content: "";
  display: block;
  width: 2.75rem;
  height: 3px;
  margin-top: 0.6rem;
  background: var(--gold);
  border-radius: 2px;
}
.panel {
  background: var(--panel);
  border: 1px solid var(--card-border);
  border-radius: 0.9rem;
  padding: 1.75rem 2rem;
  box-shadow: 0 1px 2px rgba(31, 22, 38, 0.05);
}
.empty-note h2 { margin-top: 0; font-size: 1.3rem; }
.empty-note p { margin-bottom: 0; color: var(--muted); }

/* -- rendered Markdown ------------------------------------------------ */
.prose { max-width: 40rem; }
.prose > :first-child { margin-top: 0; }
.prose > :last-child { margin-bottom: 0; }
.prose h2 {
  font-size: 1.4rem;
  margin: 2.25rem 0 0.75rem;
}
.prose h3 { font-size: 1.15rem; margin: 1.75rem 0 0.5rem; }
.prose p { margin: 0 0 1.1rem; }
.prose ul, .prose ol { padding-left: 1.4rem; margin: 0 0 1.1rem; }
.prose li { margin: 0.35rem 0; }
.prose blockquote {
  margin: 1.75rem 0;
  padding: 0.25rem 0 0.25rem 1.5rem;
  border-left: 4px solid var(--gold);
  font-family: "Fraunces", Georgia, serif;
  font-size: 1.2rem;
  line-height: 1.45;
  color: var(--purple-dark);
}
.prose blockquote p { margin: 0; }
.prose-tight { max-width: none; font-size: 0.95rem; color: var(--muted); }
.prose-tight p { margin: 0 0 0.75rem; }

/* -- card grids: Continents, Countries, Programs, Posts -------------- */
.card-grid {
  list-style: none;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr));
  gap: 1.25rem;
  margin: 0;
  padding: 0;
}
/* Posts carry more text than a destination card, so they get wider tracks —
   which lands at two across on a desktop and one on a phone. */
.card-grid.card-grid-posts { grid-template-columns: repeat(auto-fit, minmax(24rem, 1fr)); }
/* A grid of only one or two cards (a Continent with one Country, a Country
   with two Programs) shouldn't stretch them into oversized banners or leave
   a lone card hugging the left edge — cap the width and center the row.
   Excludes .card-grid-posts (#15 follow-up): a Program page's per-Topic
   post grid sits directly under its own left-aligned heading
   (.topic-group-title), so centering a single card there would float it
   away from the heading it belongs to instead of lining up under it. */
.card-grid:not(.card-grid-posts):has(> .card:only-child),
.card-grid:not(.card-grid-posts):has(> .card:first-child:nth-last-child(2)) {
  grid-template-columns: repeat(auto-fit, minmax(16rem, 22rem));
  justify-content: center;
}
.card {
  position: relative;
  display: flex;
  flex-direction: column;
  border: 1px solid var(--card-border);
  border-top: 4px solid var(--gold);
  border-radius: 0.75rem;
  padding: 1.4rem 1.5rem 1.25rem;
  background: var(--purple-light);
  box-shadow: 0 1px 2px rgba(31, 22, 38, 0.06);
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.card:hover {
  transform: translateY(-4px);
  box-shadow: 0 16px 28px -12px rgba(31, 22, 38, 0.3);
}
.card.region-0 { border-top-color: var(--region-0); }
.card.region-1 { border-top-color: var(--region-1); }
.card.region-2 { border-top-color: var(--region-2); }
.card.region-3 { border-top-color: var(--region-3); }
.card.region-4 { border-top-color: var(--region-4); }
.card.region-5 { border-top-color: var(--region-5); }
.card-title, .post-card-title {
  font-size: 1.15rem;
  margin: 0;
}
.post-card-title { margin-top: 0.6rem; }
.card-link { color: var(--ink); text-decoration: none; }
.card-link::after { content: ""; position: absolute; inset: 0; border-radius: inherit; }
.card:hover .card-link { color: var(--gold-dark); }
.card-desc {
  font-size: 0.92rem;
  color: var(--muted);
  margin: 0.5rem 0 0;
}
.card-cover {
  display: block;
  width: calc(100% + 3rem);
  height: 9rem;
  margin: -1.4rem -1.5rem 1rem;
  border-radius: 0.75rem 0.75rem 0 0;
  object-fit: cover;
}
.post-cover {
  display: block;
  width: 100%;
  height: 18rem;
  margin: 1.5rem 0 0;
  border-radius: 0.9rem;
  object-fit: cover;
}
.card-stats {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.4rem;
  margin-top: 0.75rem;
}
.card-stat-count { font-size: 0.8rem; font-weight: 600; color: var(--purple-dark); }
.card-stat-topic {
  font-size: 0.75rem;
  color: var(--muted);
  background: var(--panel);
  border: 1px solid var(--card-border);
  border-radius: 999px;
  padding: 0.1rem 0.6rem;
}
.card-cta {
  display: block;
  margin-top: auto;
  padding-top: 0.75rem;
  border-top: 1px solid var(--card-border);
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--purple-dark);
}
.card:hover .card-cta { color: var(--gold-dark); }
.info-card { background: var(--panel); }
.info-card-title { font-size: 1.2rem; margin: 0 0 0.6rem; }

/* -- bylines ---------------------------------------------------------- */
.byline {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  margin-top: auto;
  padding-top: 1rem;
}
.avatar {
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
.avatar-lg { width: 3rem; height: 3rem; font-size: 0.95rem; }
.byline-text { display: flex; flex-direction: column; line-height: 1.35; }
.byline-name { font-weight: 600; font-size: 0.9rem; }
.byline-meta { font-size: 0.82rem; color: var(--muted); }
.byline-lg { padding-top: 0; margin-top: 1.25rem; }
.byline-lg .byline-name { font-size: 1rem; }

/* -- Topic badges and filters ----------------------------------------- */
.post-topic-badge {
  align-self: flex-start;
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

.topic-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin: 0 0 2rem;
}
.topic-pill {
  border: 1px solid var(--purple);
  background: var(--panel);
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

/* -- Tag badges and filters (#14): open-ended and Staff-curated, so unlike
   Topic they get one neutral color rather than a fixed palette. -------- */
.tag-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin: 0.6rem 0 0;
}
.tag-badge {
  display: inline-block;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--muted);
  background: var(--panel);
  border: 1px solid var(--card-border);
  border-radius: 999px;
  padding: 0.15rem 0.7rem;
}
.tag-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin: -1rem 0 2rem;
}
.tag-pill {
  border: 1px solid var(--muted);
  background: var(--panel);
  color: var(--muted);
  border-radius: 999px;
  padding: 0.35rem 0.9rem;
  font: inherit;
  cursor: pointer;
}
.tag-pill.is-active { background: var(--muted); color: #fff; border-color: var(--muted); }

.post-topic-group { margin-bottom: 2.5rem; }
.post-topic-group:last-of-type { margin-bottom: 0; }
.topic-group-title {
  font-size: 1.2rem;
  margin: 0 0 1rem;
  padding-left: 0.75rem;
  border-left: 4px solid var(--topic-general);
  color: var(--purple-dark);
}
.topic-group-title.topic-general { border-left-color: var(--topic-general); }
.topic-group-title.topic-housing { border-left-color: var(--topic-housing); }
.topic-group-title.topic-meals { border-left-color: var(--topic-meals); }
.topic-group-title.topic-social-life { border-left-color: var(--topic-social-life); }
.topic-group-title.topic-academics { border-left-color: var(--topic-academics); }
.topic-group-title.topic-other { border-left-color: var(--topic-other); }

/* -- a single post ----------------------------------------------------- */
.post-title {
  font-size: clamp(2rem, 4.5vw, 2.9rem);
  margin: 0.75rem 0 0;
  max-width: 24ch;
}
/* The whole post column — article, back button, and "More from" cards —
   shares one centred measure, so nothing on the page sits on its own axis. */
.post-main { max-width: 46rem; margin-inline: auto; }
.post-article {
  max-width: none;
  padding: 2.25rem 2.5rem;
  font-size: 1.05rem;
  line-height: 1.75;
}
.post-back { margin: 1.5rem 0 0; }
.btn {
  display: inline-block;
  background: var(--purple);
  color: #fff;
  font-weight: 600;
  font-size: 0.95rem;
  text-decoration: none;
  padding: 0.65rem 1.3rem;
  border-radius: 999px;
  transition: background 0.15s ease, transform 0.15s ease;
}
.btn:hover { background: var(--purple-dark); transform: translateY(-1px); }

/* -- footer ------------------------------------------------------------ */
.site-footer {
  flex-shrink: 0;
  background: var(--purple-dark);
  color: #D9CBE8;
  padding: 2.5rem 0 1.5rem;
  border-top: 3px solid var(--gold);
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

/* -- search (#10): client-side only, against search-index.json -------- */
.site-search { position: relative; }
.search-form {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.4rem 0.75rem;
}
.search-input {
  font: inherit;
  padding: 0.4rem 0.9rem;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.35);
  background: rgba(255, 255, 255, 0.12);
  color: #fff;
  min-width: 10rem;
}
.search-input::placeholder { color: #D9CBE8; }
.search-fields {
  display: flex;
  flex-wrap: wrap;
  gap: 0.15rem 0.6rem;
  font-size: 0.78rem;
  color: #E7D9F2;
}
.search-fields label { display: inline-flex; align-items: center; gap: 0.25rem; white-space: nowrap; }
.search-results {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  margin: 0.4rem 0 0;
  padding: 0.4rem;
  list-style: none;
  background: var(--panel);
  border: 1px solid var(--card-border);
  border-radius: 0.75rem;
  box-shadow: 0 16px 28px -12px rgba(31, 22, 38, 0.3);
  max-height: 22rem;
  overflow-y: auto;
  z-index: 30;
}
.search-result { padding: 0.5rem 0.6rem; border-radius: 0.5rem; }
.search-result a { font-weight: 600; text-decoration: none; color: var(--purple-dark); }
.search-result a:hover { text-decoration: underline; }
.search-result-tags { display: block; font-size: 0.78rem; color: var(--muted); margin-top: 0.15rem; }
.search-empty { padding: 0.5rem 0.6rem; color: var(--muted); font-size: 0.9rem; }
.search-panel .search-input {
  color: var(--ink);
  background: var(--panel);
  border-color: var(--card-border);
  width: 100%;
}
.search-panel .search-input::placeholder { color: var(--muted); }
.search-panel .search-fields { color: var(--muted); }

@media (max-width: 48rem) {
  .card-grid.card-grid-posts { grid-template-columns: minmax(0, 1fr); }
  .post-article { padding: 1.75rem 1.5rem; }
}
@media (max-width: 30rem) {
  :root { --section-gap: 2.5rem; }
  .post-cover { height: 11rem; }
  .header-inner { flex-direction: column; align-items: flex-start; gap: 0.5rem; }
  .site-nav { gap: 0.4rem 1.1rem; }
  .site-footer-nav { gap: 0.4rem 1.25rem; }
  .card-grid { grid-template-columns: minmax(0, 1fr); }
  .hero { padding: 3rem 0; }
  .page-header { padding: 1.75rem 0 1.5rem; }
  .wrap { padding: 0 1rem; }
  .panel { padding: 1.4rem 1.25rem; }
  .post-article { padding: 1.5rem 1.25rem; font-size: 1rem; }
  .post-title { max-width: none; }
  .site-search { width: 100%; }
  .search-input { width: 100%; min-width: 0; }
}
@media (prefers-reduced-motion: reduce) {
  * { transition: none !important; }
  .card:hover, .hero-cta:hover, .btn:hover { transform: none; }
}
"""


# Cache-buster appended to the stylesheet link. GitHub Pages serves style.css
# with a long cache lifetime, so without this a reader who has visited before
# keeps the old design until their browser decides otherwise.
CSS_VERSION = hashlib.sha256(CSS.encode()).hexdigest()[:8]


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
) -> tuple[str, list[dict], list[dict], str]:
    """CSS path, nav, footer links, and the site-root prefix for the
    page/post living at `chain` — shared between a Page's own render and each
    of its Posts' renders. The site-root prefix (e.g. "../../") is also how a
    search result's root-relative href becomes a working link from wherever
    the search box that found it lives."""
    site_root = _relative_link(chain, [])[: -len("index.html")]
    css_path = site_root + f"style.css?v={CSS_VERSION}"
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
    return css_path, nav, footer_links, site_root


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

    # Only images actually used by published content are copied into
    # site/media/ below — a draft's or pending Post's media never reaches it,
    # same rule as its HTML never does (#15).
    used_media_ids: set[int] = set()

    # Search (#10): one JSON file at the site root, containing only published
    # Posts — a draft or pending Post never reaches it, same gate as the HTML
    # below. Every page links to it root-relatively via its own site_root.
    entries = search_index.build_index(lambda chain: "/".join(chain) + "/index.html")
    (out / "search-index.json").write_text(json.dumps(entries))

    for page in all_pages:
        if page.status != "published":
            continue
        chain = chains[page.id]
        active_id = models.nav_root_id(page, home)
        css_path, nav, footer_links, site_root = _furniture(
            chain, home, continents, footer_pages, chains, active_id
        )
        media_href = post_view.media_href_for(site_root)
        if page.cover_media_id:
            used_media_ids.add(page.cover_media_id)
        search_index_href = site_root + "search-index.json"
        breadcrumb = [
            {"title": a.title, "href": _relative_link(chain, chains[a.id])}
            for a in models.list_ancestors(page)
        ]
        is_continent = models.is_continent_page(page)
        is_country = models.is_country_page(page)
        is_program = models.is_program_page(page)
        search_scope_chain = chain if (is_continent or is_country or is_program) else None
        children = [
            post_view.page_card(
                c, _relative_link(chain, chains[c.id]), home, continents,
                stats=post_view.program_stats(c.id) if is_country else None,
                media_href=media_href,
            )
            for c in models.list_published_children(page.id)
        ]

        post_groups = None
        tag_filters = None
        if is_program:
            posts = models.list_published_posts_by_program(page.id)
            post_groups = post_view.grouped_post_summaries(
                posts, lambda post: _relative_link(chain, chain + [post.slug]),
                media_href=media_href,
            )
            tag_filters = post_view.distinct_tags(post_groups)
            for post in posts:
                if post.cover_media_id:
                    used_media_ids.add(post.cover_media_id)
                used_media_ids |= post_view.owned_media_ids(post)

        intro_md, rest_md = markdown.split_intro(page.body)
        sections = []
        if models.is_standalone_page(page):
            sections = [
                {"heading": heading, "body_html": markdown.render(body)}
                for heading, body in markdown.split_sections(rest_md)
            ]
            rest_md = markdown.strip_sections(rest_md)

        html = page_template.render(
            title=page.title,
            page=page,
            intro_html=markdown.render(intro_md),
            body_html=markdown.render(rest_md),
            sections=sections,
            region=post_view.region_index(page, home, continents),
            css_path=css_path,
            nav=nav,
            breadcrumb=breadcrumb,
            footer_links=footer_links,
            children=children,
            children_heading=post_view.children_heading(page, home),
            post_groups=post_groups,
            tag_filters=tag_filters,
            site_root=site_root,
            search_index_href=search_index_href,
            search_scope_chain=search_scope_chain,
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
                post_css_path, post_nav, post_footer_links, post_site_root = _furniture(
                    post_chain, home, continents, footer_pages, chains, active_id
                )
                post_media_href = post_view.media_href_for(post_site_root)
                post_breadcrumb = [
                    {"title": a.title, "href": _relative_link(post_chain, chains[a.id])}
                    for a in models.list_ancestors(page)
                ] + [{"title": page.title, "href": _relative_link(post_chain, chain)}]
                more_from = [
                    post_view.post_summary(
                        other, _relative_link(post_chain, chain + [other.slug]),
                        media_href=post_media_href,
                    )
                    for other in models.list_published_posts_by_program(page.id)
                    if other.id != post.id
                ][:2]
                post_html = post_template.render(
                    title=post.title,
                    post=post,
                    topic_label=summary["topic_label"],
                    tags=summary["tags"],
                    cover=post_view.media_cover(post.cover_media_id, post_media_href),
                    author_name=summary["author_name"],
                    author_role=summary["author_role"],
                    author_initials=summary["author_initials"],
                    published_date=summary["published_date"],
                    body_html=markdown.render(
                        post.body, media_href=post_view.post_body_media_href_for(
                            post, post_site_root
                        )
                    ),
                    region=post_view.region_index(page, home, continents),
                    css_path=post_css_path,
                    nav=post_nav,
                    breadcrumb=post_breadcrumb,
                    footer_links=post_footer_links,
                    program_href=_relative_link(post_chain, chain),
                    program_title=page.title,
                    more_from=more_from,
                    site_root=post_site_root,
                    search_index_href=post_site_root + "search-index.json",
                )
                post_dir = out.joinpath(*post_chain)
                post_dir.mkdir(parents=True, exist_ok=True)
                (post_dir / "index.html").write_text(post_html)

    if used_media_ids:
        media_out = out / "media"
        media_out.mkdir(parents=True, exist_ok=True)
        for media_id in used_media_ids:
            media = models.get_media_by_id(media_id)
            if media is None:
                continue
            src = settings.MEDIA_DIR / media.filename
            if src.is_file():
                shutil.copy2(src, media_out / media.filename)

    return out
