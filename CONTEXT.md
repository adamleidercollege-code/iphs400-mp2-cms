# Kenyon CGE Study Abroad CMS

Glossary for the CMS built for the Kenyon Center for Global Engagement's study
abroad blog. Client: `notes/client-brief.md`. The 7 fixed capabilities this
vocabulary has to satisfy: `docs/manual_iphs400_mp2-web-cms_20260922.md` §3.3.

## Language

**Page**:
Site content with a parent — except Home, which has none. Most Pages sit in
the Continent → Country → Program tree below Home, but a Page can also stand
alone under Home directly, like About CGE or Contact Us. Home's own body
lists the Continents, full stop — standalone Pages under Home don't appear
there. Every other Page's body lists its non-footer child Pages, if it has
any, and its own Posts grouped by Topic, if it has any — no separate
template per level otherwise. A reader finds a Page three ways: the top nav
bar (Home plus the Continents, always, regardless of what else exists), a
breadcrumb trail built from its parent chain (e.g. Home → Asia → Japan →
Kenyon-in-Kyoto), and the footer, which lists any Page with its "show in
footer" flag checked — a standalone Page under Home is only reachable this
way, so it's expected to always have that flag checked. Staff add more
Continents, Countries, Programs, and standalone Pages later through the
normal page editor, the same way the seed set was created.
_Avoid_: continent page, country page, program page as if they were distinct
types — they are all just Pages at different places in the tree. Also avoid
assuming every Page is travel content — About CGE and Contact Us are Pages
too, just standalone ones under Home.

**Continent**:
A Page one level below Home — Asia, Africa, and Europe in the seed data. Lists
its child Country Pages.

**Country**:
A Page one level below a Continent. Lists its child Program Pages.

**Program**:
A Page one level below a Country — the level Posts are written under. Lists
its own Posts, grouped by Topic, with a filter by Topic.

**Post**:
A dated blog entry written under a Program Page: title, slug, Markdown body,
Topic, author, timestamps, and a status of draft, pending, or published.
_Avoid_: entry, article.

**Slug**:
The URL-safe name derived from a Post's or Page's title. Nobody edits it by
hand — it regenerates automatically whenever the title changes while the
content is still draft, then freezes the moment it's published, so a shared
link never breaks. Shown read-only wherever the content is edited.
_Avoid_: implying it's a form field a Staff or Ambassador fills in — it has
no input of its own, only a display.

**Topic**:
The category a Post is tagged with, used to group and filter Posts on their
Program page like forum sections (read-only — no replies or discussion):
General, Housing, Meals, Social Life, Academics, or Other.
_Avoid_: treating General as a different kind of thing from the rest — see
Hot Topic for how the two relate.

**Hot Topic**:
Any Topic value other than General — Housing, Meals, Social Life, Academics,
or Other. The brief and field notes' informal name for that subset; there is
no separate field for it, only Topic.
_Avoid_: treating Hot Topic as a type distinct from Topic, or as a field of
its own — see Topic.

**Tag**:
A Staff-curated label an Ambassador or Staff member attaches to their own
Post from an existing list — unlike Topic, a Post can carry any number of
Tags, and nobody chooses one that doesn't already exist. Tags live
independently of Topic: a Post keeps exactly one Topic (its forum section)
and zero or more Tags (free-form, cross-cutting labels like visa or
homestay) at the same time. Staff alone create, rename, and delete Tags,
from a Tags screen in the Staff sidebar; an Ambassador picks only from what's
already there. Shown on a Post's card and its own page, and usable as a
second, independent filter alongside Topic on a Program page — there is no
sitewide tag listing.
_Avoid_: calling a Tag a Topic or treating it as a replacement for Topic —
the two coexist: Topic is single-select and fixed to six values; Tag is
multi-select and Staff-extensible.

**Status** (of a Post):
draft → pending → published. *Draft*: the author is still writing; only they
can edit it, and it is not public. *Pending*: the author has submitted it for
review and can no longer edit it; it is still not public — anyone with the
admin role can act on it, not just a specific reviewer, and there is no
notification when a Post lands in the queue. *Published*: live on the public
site. Only an admin can move a Post into or out of published, and only an
admin can bounce pending back to draft. One shortcut: an admin can publish
their own draft directly, skipping pending, since there is no one else to
review it against; an admin's draft can also go through pending like anyone
else's if they want another admin's eyes on it first. The shortcut applies
only to an admin's own Post — an admin cannot push someone else's draft
straight to published without it passing through pending. If the author's
account is later deactivated, what happens to a draft depends on their role:
an Ambassador's draft is deleted (nothing worth keeping from a student who's
left, and it would otherwise clutter the content list); a Staff member's
draft is left exactly as it is — it's usually CGE's own ongoing work, not a
departing student's, and any other Staff member can already view, edit,
publish, or delete it like any other Post. Either way, a pending Post is
left alone, since Staff still need to act on it, and a published Post is
left alone too and keeps its byline, since its value to readers has nothing
to do with whether its author's account is still active.
_Avoid_: treating pending as a synonym for draft — the manual's capability list
names only draft/published, but this project adds pending as the explicit
submit-for-review step the client asked for (see ADR-004).

**Role**:
Two roles, per the manual: *admin*, shown in the UI as **Staff**, and *editor*,
shown in the UI as **Ambassador**. The mapping is strict and permission-based,
not title-based — admin/editor stay the internal/code names (the manual's own
vocabulary); Staff/Ambassador are what the site and this glossary call them.
Staff have every capability Ambassadors have (they can write and submit Posts
too) plus admin-only capabilities (publish, user management).
_Avoid_: "CGE staff" / "student ambassador" in place of Staff/Ambassador once
inside the CMS's own vocabulary — those are brief language, not the product's.

**Staff**:
The UI-facing name for the admin role (see Role). Can manage users; create,
edit, delete, and publish any Page or Post; and do everything an Ambassador
can, including writing and submitting their own Posts — with the option to
either self-publish a draft directly or submit it to pending like anyone
else (see Status).
_Avoid_: "CGE staff", admin — see Role.

**Ambassador**:
The UI-facing name for the editor role (see Role): a student who writes and
submits their own Posts. Can create, edit, and delete only their own Posts,
and only while draft (see Status); cannot touch another user's Post, cannot
create or edit a Page, and cannot publish.
_Avoid_: "student ambassador", editor — see Role.
