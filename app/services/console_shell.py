"""Shared chrome for every server-rendered admin screen: the sidebar nav,
the relative stylesheet link, and post-save flash messages. Every
`app/routes/*.py` module except `public.py` uses this (the public site has
its own, unrelated live-preview chrome in `app/routes/public.py`).

Issue #13: the admin console's stylesheet link is relative and
depth-computed (see app.services.css_path) rather than root-absolute —
a literal `href="/..."` would still work on this live server, but
`scripts/check_submission.py` greps every tracked template for
root-absolute paths regardless of whether the page is ever statically
exported, so this stays relative like everything else.
"""
from __future__ import annotations

from urllib.parse import quote

from fastapi import Request
from fastapi.responses import RedirectResponse

from app import models
from app.routes.auth import ensure_csrf_token
from app.services.css_path import css_path_for

SIDEBAR = [
    ("/admin/dashboard", "Dashboard"),
    ("/admin/content", "Content list"),
    ("/admin/pending", "Pending queue"),
    ("/admin/accounts", "Accounts"),
    ("/admin/pages", "Page hierarchy"),
    ("/admin/tags", "Tags"),
    ("/admin/metrics", "Metrics"),
]

EDITOR_SIDEBAR = [
    ("/admin", "My posts"),
]


def console_context(request: Request, user: models.User, sidebar=None) -> dict:
    """The csrf token, stylesheet path, and sidebar every authenticated
    admin screen needs. Defaults the sidebar by role (Staff vs Ambassador)
    so most call sites don't have to pick one themselves."""
    chosen = sidebar or (SIDEBAR if user.role == "admin" else EDITOR_SIDEBAR)
    return {
        "user": user,
        "csrf_token": ensure_csrf_token(request),
        "css_path": css_path_for(request),
        "sidebar": [{"href": href, "label": label} for href, label in chosen],
    }


def redirect_with_flash(
    url: str, message: str, *, fragment: str | None = None, **extra_params: str
) -> RedirectResponse:
    """A 303 redirect carrying a one-time success message, read back by
    templates/base.html's `request.query_params`. No session state: a
    refresh of the destination page just drops the message, which is fine
    for a "your save worked" banner.

    `fragment` and `extra_params` (#15 follow-up) let a caller land the
    reader on a specific part of a long page — e.g. an image upload redirect
    jumps straight to that upload section instead of the top of the post
    form, with `extra_params` carrying which Media was just added so the
    template can show its thumbnail there. The fragment is appended last,
    since a URL fragment must come after the query string to be valid.
    """
    sep = "&" if "?" in url else "?"
    target = f"{url}{sep}flash={quote(message)}"
    for key, value in extra_params.items():
        target += f"&{key}={quote(str(value))}"
    if fragment:
        target += f"#{fragment}"
    return RedirectResponse(url=target, status_code=303)


# Reuses the public site's Kenyon purple + gold palette and Fraunces/Inter
# fonts (app/publish.py's CSS) for a consistent look, but is otherwise
# self-contained: the admin console's HTML (sidebar, forms, plain <ul> lists
# standing in for tables) is different enough from the public site's that
# sharing one stylesheet would mean every admin rule risks colliding with a
# public one, or vice versa.
ADMIN_CSS = """/* Admin console shell — issue #13. Same palette/fonts as the
   public site (app/publish.py's CSS), different components: a sidebar
   layout, plain lists standing in for tables, and HTML forms. */
:root {
  color-scheme: light dark;
  --purple: #5B2A86;
  --purple-dark: #3E1C5E;
  --purple-light: #F2EBFA;
  --gold: #C98A3B;
  --gold-dark: #9C6723;
  --ink: #1F1626;
  --muted: #5a5064;
  --border: #E4DCEC;
  --paper: #FDFBFE;
  --panel: #FFFFFF;
  --danger: #B3261E;
  --danger-dark: #8C1D16;
  --danger-bg: #FBE9E4;
  --success-bg: #E3F3EF;
  --success-border: #2E7D6B;
}
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body {
  font: 16px/1.6 "Inter", system-ui, sans-serif;
  margin: 0;
  color: var(--ink);
  background: var(--paper);
  overflow-wrap: anywhere;
}
h1, h2 { font-family: "Fraunces", Georgia, serif; line-height: 1.2; margin: 0 0 1rem; }
h2 { font-size: 1.25rem; margin-top: 2rem; }
a { color: var(--purple-dark); }
:focus-visible { outline: 3px solid var(--gold); outline-offset: 2px; border-radius: 2px; }

header.site-header {
  background: var(--purple);
  padding: 0.85rem 1.5rem;
}
header.site-header .brand {
  color: #fff;
  font-family: "Fraunces", Georgia, serif;
  font-weight: 600;
  font-size: 1.1rem;
}
main { padding: 1.5rem; max-width: 68rem; margin: 0 auto; }
footer { padding: 1rem 1.5rem; color: var(--muted); font-size: 0.85rem; }

.flash {
  background: var(--success-bg);
  border: 1px solid var(--success-border);
  color: #1c4038;
  padding: 0.7rem 1rem;
  border-radius: 0.5rem;
  margin: 0 0 1.25rem;
  font-weight: 600;
}
[role="alert"] {
  background: var(--danger-bg);
  border: 1px solid var(--danger);
  color: var(--danger-dark);
  padding: 0.7rem 1rem;
  border-radius: 0.5rem;
  margin: 0 0 1.25rem;
  font-weight: 600;
}

/* -- forms ------------------------------------------------------------- */
form { margin: 0 0 1.25rem; }
label { display: block; margin: 0 0 0.9rem; font-weight: 600; font-size: 0.9rem; color: var(--muted); }
input[type="text"], input[type="email"], input[type="password"], select, textarea {
  display: block;
  margin-top: 0.3rem;
  width: 100%;
  max-width: 32rem;
  font: inherit;
  padding: 0.5rem 0.7rem;
  border: 1px solid var(--border);
  border-radius: 0.4rem;
  background: #fff;
  color: var(--ink);
}
input[type="checkbox"] { width: auto; display: inline-block; margin-right: 0.4rem; }
textarea { min-height: 9rem; font-family: ui-monospace, "SFMono-Regular", monospace; font-size: 0.9rem; }
input:focus, select:focus, textarea:focus { border-color: var(--purple); }

button, .btn {
  font: inherit;
  font-weight: 600;
  font-size: 0.95rem;
  border: none;
  border-radius: 999px;
  padding: 0.5rem 1.2rem;
  background: var(--purple);
  color: #fff;
  cursor: pointer;
  text-decoration: none;
  display: inline-block;
}
button:hover, .btn:hover { background: var(--purple-dark); }
button.btn-danger { background: var(--danger); }
button.btn-danger:hover { background: var(--danger-dark); }

.post-preview, .preview-pane {
  border: 1px solid var(--border);
  border-radius: 0.6rem;
  padding: 1rem 1.25rem;
  background: #fff;
  max-width: 40rem;
}
/* Same overflow fix as app.publish's .prose img, for the live admin
   preview of a Post's body (templates/admin/posts_form.html). */
.post-preview img, .preview-pane img { max-width: 100%; height: auto; }

/* -- image upload sections (#15 follow-up) ------------------------------ */
/* A light bordered box around each upload section (templates/admin/
   posts_form.html's Cover image / Add an image to the body, and
   pages_form.html's Cover image) — otherwise two near-identical forms
   back to back are hard to tell apart at a glance. */
.upload-box {
  border: 1px solid var(--border);
  border-radius: 0.6rem;
  padding: 1rem 1.25rem;
  margin: 0 0 1.5rem;
  background: #fff;
}
.upload-box h2 { margin-top: 0; }
/* The just-added confirmation (redirected back from a successful upload,
   console_shell.redirect_with_flash's `fragment`/`added_media_id`): the
   usual flash banner plus a small thumbnail of the image itself. */
.upload-added { display: flex; align-items: center; gap: 0.6rem; }
.upload-added img {
  width: 2.75rem;
  height: 2.75rem;
  object-fit: cover;
  border-radius: 0.3rem;
  flex-shrink: 0;
}

/* -- lists standing in for tables --------------------------------------- */
ul { list-style: none; margin: 0; padding: 0; }
main ul li {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.6rem;
  padding: 0.7rem 0.9rem;
  border: 1px solid var(--border);
  border-radius: 0.5rem;
  margin: 0 0 0.6rem;
  background: #fff;
}
main ul li form { margin: 0; }

/* The Page hierarchy tree nests arbitrarily deep — indent it instead of
   boxing every level like a flat row list. */
.page-tree, .page-tree ul { padding-left: 0; }
.page-tree li, .page-tree li li {
  display: block;
  border: none;
  background: none;
  padding: 0.3rem 0 0.3rem 0.9rem;
  margin: 0;
  border-left: 2px solid var(--border);
}

/* -- the Staff/Ambassador console shell --------------------------------- */
.console { display: flex; align-items: flex-start; gap: 0; }
.console-sidebar {
  flex: 0 0 15rem;
  background: var(--purple-light);
  border-radius: 0.6rem;
  padding: 1.1rem;
  margin-right: 1.75rem;
}
.console-sidebar p { margin: 0 0 0.6rem; font-size: 0.9rem; color: var(--muted); }
.console-sidebar nav ul { margin-top: 0.75rem; }
.console-sidebar nav li {
  display: block; border: none; background: none; padding: 0; margin: 0 0 0.25rem;
}
.console-sidebar nav a {
  display: block;
  padding: 0.45rem 0.6rem;
  border-radius: 0.4rem;
  color: var(--purple-dark);
  font-weight: 600;
  text-decoration: none;
}
.console-sidebar nav a:hover { background: #fff; }
.console-main { flex: 1; min-width: 0; }

@media (max-width: 30rem) {
  main { padding: 1rem; }
  .console { flex-direction: column; }
  .console-sidebar { flex: none; width: 100%; margin: 0 0 1.25rem; }
  input[type="text"], input[type="email"], input[type="password"], select, textarea,
  .post-preview, .preview-pane { max-width: none; }
}
"""
