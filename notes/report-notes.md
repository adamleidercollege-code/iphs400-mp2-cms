# Report notes

## Q1: What I built + grill decisions that were MINE
- Client: Kenyon CGE study abroad blog (picked it because I'm going to DIS Copenhagen in spring).
- Overrode Claude:
  - Q3: Claude wanted "CGE staff"/"student ambassador" as words to AVOID. I kept Staff/Ambassador as the UI names (admin/editor in code).
  - Q10: Claude recommended editable slugs. I said auto-generated and NOT editable (ambassadors won't know what a slug is), frozen once published.
  - Q12: Kept the WordPress-style landing (site preview as home, sidebar tabs) instead of a plain dashboard page.
  - Spec flag 3: Claude assumed Staff drafts get deleted on deactivation like Ambassadors'. I changed it so Staff drafts are kept.
- My own additions: pending "submit for review" status, Continent→Country→Program page tree with demo data, topics on posts with a filter, footer pages (About/Contact), nav bar + breadcrumbs, ambassador drafts deleted when deactivated, "are you sure?" before delete.
- Scope cuts I chose: trash/auto-delete, scheduled publishing, suggested edits, messaging/comments (all need a live server or extra features). Search kept as a stretch ticket.

## Q2: Drift (what the AI made up + what caught it)
- Spec #1: Claude filled in decisions I never made (slug -2/-3 suffixes, Staff can't publish others' drafts directly, Staff drafts deleted on deactivation). Caught by reading the spec before tickets.
- T01 (#2): code showed raw role codes "admin/editor" in the UI instead of Staff/Ambassador from CONTEXT.md. Caught by /code-review. Fixed with User.role_label.
- Design passes (T11): Claude started calling posts "dispatches" in the hero, footer and headings. Not in CONTEXT.md, where the term is "Post". I caught it by reading the live site and had it changed to match the glossary.

## Q3: Skills, prompts, resources
- Skills: /grill-with-docs, /to-spec, /to-tickets, /implement, /tdd, /code-review, /setup-matt-pocock-skills

- Prompts I actually used (quote these word for word in the README):
  - Prompt 1 (grill answer A3, my own words):
    "A CGE staff member should be able to write posts as well if they desire, they should possess all the tools that the ambassador role provides. The role names can be staff and ambassador."
  - Prompt 2 (test seams, before /to-spec):
    "Those two seams match was I was expecting, but could you also do a third one: a small services layer for the pure rules like slug generation, the status transitions (who can move a post from a draft to pending to published and back), and what happens to an ambassadors posts when they're deactivated. Those rules are really the core of how the CGE's review works, so I want them to be tested directly as opposed to only through HTTP, and this will keep the code splits into models, routes, templates, and services."
  - How I started: the /grill-with-docs kickoff for the CGE study abroad blog (mostly drafted with help).
  - TODO: check both quotes against docs/transcripts/ to make sure they match exactly what I sent.

## Q4: Budget + what I'd add next
- Plan said opusplan/Opus high for grill/spec/tickets. Ledger shows it ran on Sonnet 5 high. I believe my computer restarted and I forgot to shift the model back when I began again.
- usage_report.py after T01 (Oct 5, 2:11 am):

      phase          turns  5h spent   weekly  models / provider
      T01                4      4.0%     0.0%  Sonnet 5
      grill             14     23.0%     6.0%  Sonnet 5
      setup             14     16.0%    14.0%  Opus 5,Sonnet 5,Test
      spec               4      4.0%     1.0%  Sonnet 5
      tickets            3      4.0%     1.0%  Sonnet 5
      unlabelled        16     10.0%     2.0%  Sonnet 5

      Tickets done: 1 · average weekly cost per ticket: 0.0%
      Forecast: 7 tickets need ~0% of the weekly cap; 62% remains → FITS

- Plan vs actual: planned 30% of a 5h window per ticket (20 implement + 10 review); T01 actually cost 4%. Grill planned 30%, actual 23%. I overestimated tickets by a lot.
- The "0% weekly per ticket" is a rounding artifact: the weekly meter only moves in whole numbers, so T01 cost under 1%, not zero.
- The "Test" model in the setup row is a fake test row from Oct 1, not real usage. I left it in the ledger rather than edit graded evidence.
- 16 turns are "unlabelled" because I didn't always set the phase before starting work.
- Next: trash with restore, scheduled publishing, suggested edits, private messaging, visitor accounts, search filters by views.
- usage_report.py after T03 (Oct 5, 5 pm):
  - T01 5% of a 5h window / 1% weekly · T02 17% / 5% · T03 15% / 2%
  - Avg ~12% of a window and 2.7% weekly per ticket, vs my plan of 30% per ticket. I overestimated by more than half.
  - T02 cost the most (four review fixes + first deploy). T03's hung review added cost too.
  - Forecast: 5 tickets need ~13% of the weekly cap, 54% remains → FITS.

## Real model failures (README needs at least 1)
- Claude ran the submission checker with the wrong Python, reported a test failure that wasn't real, then caught and corrected it.
- /setup-matt-pocock-skills skipped creating the spec/ticket/stretch labels the project needed.
- /code-review's background fork hung 36+ min (T03); Claude then reviewed its own code. Rerunning with a fresh foreground subagent fixed it.
- A /loop wakeup kept re-firing after tickets were done, re-prompting Claude for nothing.
- Claude committed T07 but didn't push, so issue #8 stayed open. Added a CLAUDE.md rule to push and confirm CLOSED.
- Claude said it couldn't take screenshots until I had it install Playwright.

## Things that went wrong (good for report voice)
- Grill session crashed twice; recovered with claude --resume / fg after accidentally hitting Ctrl+Z.
- Did the grill in an Orca worktree on a side branch by accident; had to merge it into main.
- Transcripts were saving as "your-name": the template had no CMS_STUDENT setting. Fixed in .env/.env.example.
- Found settings.json had the context warnings lowered to 30/40%; reverted to the course's 50/60/80.

## T02 (#3)
- /code-review caught that deleting the Home page would wipe the ENTIRE page tree in one click (cascade delete), and the system would quietly rebuild an empty Home. Tests hadn't caught it. Fixed: Home can't be deleted. Biggest review catch so far.
- My issue #3 comment first got posted from my school account (leider1) because my browser was logged into it; reposted from adamleidercollege-code.
- First deploy: the site was live but just bare black text. The stylesheet was the template's minimal starter, not a broken path. Added design + 390px phone width to T05's (#6) acceptance criteria.
- GitHub Pages turned itself on when the gh-pages branch was first pushed.

## T03 (#4)
- /code-review's background fork hung for 36+ minutes; had to stop it. Claude then reviewed its own diff, which breaks the "reviewer ≠ author" rule.
- Had it retry with a fresh, independent subagent. That finished in ~2 min, found no bugs, and flagged one UX nitpick (the new-post form opened under a continent/country page only errors on Save). I fixed it because I didn't want the user having to go through the extra effort and annoyance of writing their whole post only to realize it was in the wrong location at the end.

## T04 (#5)
- Built the review gate: draft → pending → published, with Staff able to publish their own drafts directly and Ambassadors needing review. 103 tests passing.
- Review (high effort) caught a race condition: two Staff acting on the same pending post at once could silently overwrite each other. Fixed so the second one gets an error. Very relevant for CGE, where several staff could open the pending queue at once.
- Also caught: the status rules written in two places (could drift apart), and unpublishing kept the old "published on" date.
- The background /code-review didn't hang this time but I was ready to rerun it in the foreground. Added a CLAUDE.md rule to always use a foreground subagent for reviews.
- My comment on #5 was my 3rd own-words comment (A5 needs 3).

## T05 (#6)

- The T05 design was built but never went live: my deploy command silently stopped because seed_demo.py couldn't read .env (nothing loaded it). Caught only by checking the live site. That also would have broken the grader's clean-clone setup. Fixed by making the scripts load .env themselves.
- Built public posts on program pages (grouped by topic, with a filter) plus the first Kenyon-purple design, which I added to the ticket myself after the plain first deploy.
- Review flagged an out-of-scope gap: the admin preview could show a published post under a draft program. I left it as-is because only CGE Staff can see the preview, and the real public site already hides anything under an unpublished program.

## T06 (#7)
- Built the Staff-only Accounts tab: create users, deactivate/reactivate, plus my deactivation rules (Ambassador drafts deleted; pending/published kept; Staff drafts kept). Seed data shows both cases.
- Review (fresh foreground subagent) found no blocking issues.
- Gap the review missed: there was no way to CHANGE an existing user's role, which the rubric requires (C6). I caught it by checking the summary against the rubric. Added it as a "T06 follow-up" commit with 3 tests, including one proving an Ambassador can't promote themselves to Staff.
- 135 tests passing.

## T07 (#8)
- Built the Staff console the way I designed it in the grill (A12): site preview as the Staff home screen, sidebar with Dashboard, Pending queue, Accounts, Page hierarchy, Metrics. Metrics = posts per program, including programs with zero posts, so CGE can see where they need ambassadors.
- Biggest ticket so far (~25 min). Review subagent took ~4 min and found no bugs, two minor notes.
- 145 tests passing.

## T08 (#9)
- Ambassador "My posts" screen: their own posts grouped by draft/pending/published, a sidebar with only "My posts", 403 on every Staff page.
- Claude removed a T07 test assertion that checked the old Ambassador landing page. Legit, since T08 replaced that page, but worth noting that tests changed.
- Review found no bugs. 150 tests passing. All 8 core tickets done.

## T10 (#11) + T11 (#12): design
- My own ticket, added after T05: the site was purple but narrow and plain. Full-width layout, home hero, card grids, Kenyon purple + gold, Fraunces/Inter fonts, footer disclaimer that it's a demo, not an official Kenyon page.
- Review found no bugs, two small nits fixed. 150 tests passing.
- First design pass was generic. I pushed for a second pass with a concrete "travel magazine" direction.
- Claude said it couldn't screenshot; I had it install Playwright and write scripts/screenshot.py so it could actually look at its work. The screenshots caught a real bug (topic badges squished into blobs at 1280px).
- Relabeled both as stretch to keep core tickets at 8.

## Lesson
- T01's review findings were fixed and posted without me weighing in. From T02 on, I read the findings and replied in my own words on the issue.

## Problem note

- Oct 6: local git database got corrupted (empty object files, probably from one of the crashes/force-closes). Everything was on GitHub, so I re-cloned and copied over the unpushed transcripts and ledger. Also found two Claude sessions had run in the Orca worktree and saved misnamed transcripts there.

## Design notes

- Design round 2 (T11 follow-up): I reviewed the live site myself and found dead About/Contact links (a real broken-link bug), program pages with "No posts yet", leftover placeholder text, a footer floating mid-page, and flags rendering as "JP"/"KR" on Windows. All fixed, plus a link-crawler test. Two review rounds each caught more issues.
- Lesson: tests and reviews passed while the site still had obvious problems. Only looking at it myself caught them.
- Drift: during the design passes Claude started calling posts "dispatches" (hero, footer, headings). Not in CONTEXT.md, where the term is "Post". I flagged it; in the final pass Claude spotted my note and asked before renaming everything to "posts".
- Final design pass on Opus (high): fixed dead space, About/Contact layouts, richer post pages, breadcrumbs. Hit my 5h limit mid-review (HTTP 429), then my computer restarted with the work uncommitted. Nothing lost; switched back to Sonnet to test, review, commit and deploy.
- The review caught a real bug: a continent marked "show in footer" would silently vanish from the nav.
- Claude changed 4 older test files; I made it justify each. They only tracked renamed demo authors, and no checks were weakened.
- I removed the "dispatch" strips from Home, continent, country and About/Contact pages (felt gimmicky); kept posts on program pages and "More from [Program]" on posts.

## Stage 1 (Oct 5)
- check_submission flagged admin templates using "/..." links (fixed), the missing mp2-mvp tag (tagged), and "secrets in history": 2 false positives inside transcripts, not real keys. Didn't rewrite history; explained it in my Stage 1 email.

## Placeholder slot
- Final usage_report.py (after the last deploy): PASTE HERE
- The Opus design pass hit my 5h limit. Opus has better design taste but burns the window much faster than Sonnet.