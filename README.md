# Kenyon CGE Study Abroad CMS

A small web CMS built for the Kenyon Center for Global Engagement (CGE)'s study
abroad blog (IPHS 400 Mini-Project #2). A local admin console (FastAPI + Jinja
+ SQLite) is where Staff and Ambassadors write and review content; `cms publish`
renders only the published content into `site/` as static HTML, deployed to
GitHub Pages. The admin console itself never goes on the public internet.

Claude Code was used throughout this project. I took more of a manager and planner's role: answering the grill questions and overriding Claude on a number of occasions, reading and criticizing the spec, checking results and editing until the desired outcome was achieved, and pushing for specific designs that I had in my mind. I picked the stretch goals myself, and added to each of the other goals as well. Throughout the process, I updated CLAUDE.md and set rules to ensure that we were moving through the project in a way that was aligned with my intentions. I also tested the site as a user, allowing me to suggest edits and critique from the position of somebody using my product. I used chat Claude in my browser to assist with prompt engineering and project organization/management, and I used Claude Code to build the tool itself. 

## Live URL

Public site: https://adamleidercollege-code.github.io/iphs400-mp2-cms/

Repo: https://github.com/adamleidercollege-code/iphs400-mp2-cms

## Features

The 7 required capabilities, built for this client:

1. **Login** — Staff and Ambassadors sign in and out; passwords hashed with argon2, never stored or logged in plain text.
2. **Two roles** — **Staff** (`admin`) and **Ambassador** (`editor`), with genuinely different permissions: Staff can do everything an Ambassador can, plus publish, manage users, and manage the page tree.
3. **Posts** — full CRUD; title, auto-generated slug (frozen once published), Markdown body, draft → pending → published status, author, timestamps, one Topic, any number of Tags.
4. **Pages** — a Continent → Country → Program tree below Home, plus standalone pages (About, Contact); published pages appear in the public nav and breadcrumbs.
5. **Admin console** — dashboard with counts, a filterable content list, a post editor with a live preview, and a page editor. 
6. **User management** — Staff-only: create users, change roles, deactivate/reactivate; a deactivated user cannot log in, and deactivation rules differ by role (an Ambassador's drafts are deleted, a Staff member's are kept).
7. **Public site and publish** — only published content reaches `site/`; Markdown is sanitized before render; nav is built from published pages; `cms publish` writes relative paths only.

Stretch features added beyond the required 7:

- **Tags** — Staff-only creation, filterable within a Program, independent of Topic.
- **Search** — runs entirely client-side from a JSON index built at publish time, scoped to a section or sitewide, so it works on GitHub Pages with no server.
- **Media** — post covers and inline images set by the author; program covers set by Staff; uploads are resized, rotated upright, and stripped of EXIF/GPS data.
- **Formatting help** — a "You type → You get" Markdown help box in the post and page editors, for Ambassadors who don't already know Markdown.

## Run locally

```bash
git clone https://github.com/adamleidercollege-code/iphs400-mp2-cms.git
cd iphs400-mp2-cms
uv sync
cp .env.example .env
uv run python scripts/seed_demo.py   # optional: seeds demo Staff/Ambassador accounts and sample content
uv run cms serve                     # http://localhost:8000/admin
```

Demo accounts created by the seed script (from `.env.example`'s default passwords):
`admin@example.test` / `change-me-admin` (Staff), `editor@example.test` / `change-me-editor` (Ambassador).

Run the test suite with `uv run pytest -q`.

Verified 2026-10-08 on a fresh clone in a scratch directory: `uv sync`, `cp .env.example .env`,
and `uv run python scripts/seed_demo.py` all ran unmodified; `uv run pytest -q` passed 226/226;
`uv run cms serve` came up clean and `/` and `/admin` both returned HTTP 200. Nothing failed.

To publish the public site from what's currently published in the database:

```bash
uv run cms publish   # writes site/
uv run cms deploy    # pushes site/ to the gh-pages branch
```

## Generative AI Use Statement

While I made the majority of design decisions in this project, Claude did help with some things. The structure of the site, such as the names of the roles, the site tree design, the overall structure, the formatting help box for markdown in the post section, locked slugs once published, most of the design details like those were decided by me, with Claude making the smaller implementation and coding decisions. For a number of these implementations, Claude suggested a plan, and I edited or changed it (editable to permanent slugs (because ambassadors won't know what a slug is), staff work being kept after their accounts get deactivated). Claude did solve a few problems I wouldn't have noticed otherwise, like implementation problems that I have little experience with, such as two staff members potentially working on and publishing the same post at once. Overall, I made the majority of design decisions and Claude implemented them, but there was some crossover on both sides. 

### Models and skills used

Built with [Claude Code](https://claude.com/claude-code) (Anthropic), using these
Claude Code skills throughout the grill → spec → tickets → implement → review loop:
`/grill-with-docs`, `/to-spec`, `/to-tickets`, `/implement`, `/tdd`, `/code-review`,
`/handoff`, `/setup-matt-pocock-skills`.

### Backends used

| Provider | Model | Ledger rows | Used for |
|---|---|---|---|
| anthropic | Sonnet 5 | 190 | grill, spec, tickets, implementation, review, and deploy — nearly the whole project |
| anthropic | Opus 5 | 4 | setup and the T11 design pass (better design taste, but burned the 5-hour usage window much faster than Sonnet) |
| anthropic | Test | 2 | a fake row from an Oct 1 ledger test, not real usage — left in `notes/usage-ledger.csv` rather than edit graded evidence |
| anthropic | Claude (claude.ai chat) | not in ledger | step-by-step guidance and drafting prompts for Claude Code; not tracked by the usage ledger |

No non-Anthropic backend (e.g. OpenRouter, Z.ai) was used anywhere in this project — every row in the ledger is `anthropic`.

### Two prompts I actually sent

Prompt 1 (grill answer A3, session 16):

> A CGE staff member should be able to write posts as well if they desire; they should have all the tools the ambassador role has. The role names shown in the site and CONTEXT.md can be Staff and Ambassador, but in the code they stay admin (Staff) and editor (Ambassador).

Prompt 2 (test seams, before `/to-spec`):

> Those two seams match was I was expecting, but could you also do a third one: a small services layer for the pure rules like slug generation, the status transitions (who can move a post from a draft to pending to published and back), and what happens to an ambassadors posts when they're deactivated. Those rules are really the core of how the CGE's review works, so I want them to be tested directly as opposed to only through HTTP, and this will keep the code splits into models, routes, templates, and services.

### Real model failures

- Claude ran the submission checker with the wrong Python, reported a test failure that wasn't real, then caught and corrected it.
- `/setup-matt-pocock-skills` skipped creating the spec/ticket/stretch labels the project needed.
- `/code-review`'s background fork hung 36+ minutes (T03); Claude then reviewed its own code, breaking the "reviewer ≠ author" rule. Rerunning with a fresh foreground subagent fixed it.
- A `/loop` wakeup kept re-firing after tickets were done, re-prompting Claude for nothing.
- Claude committed T07 but didn't push, so issue #8 stayed open.
- Claude said it couldn't take screenshots until Playwright was installed for it.
- While verifying flash messages, Claude created a stray "Flash Test" account in the real local demo database instead of a test copy. It caught and deleted it before the screenshots.
- Claude (chat) stated that "Add image" inserts the Markdown line for you, as fact, before checking; when asked, it admitted it was inferring. It turned out to be true, but it was verified before writing the help box around it.
- The admin console was never styled (`style.css` 404 on every nested admin page) through the entire build; nothing caught it — not the tests, not any review — until the required screenshots were taken (#13).

The failure that mattered the most to me was probably the review hang. The review hung and ran for 36 minutes, which first took a great deal of my time, but second, after the review hung, Claude proceeded to review its own code without an external reviewer. The external review function exists to ensure security and efficiency - if a Claude agent reviews its own work, it's much more likely to approve it. Fortunately, the issue was caught and I reran the code review with a fresh subagent, subsequently adding a CLAUDE.md rule to always run reviews that way, which later caught a number of real bugs, such as the race condition, the footer bug, and the PR #17 image leak. 