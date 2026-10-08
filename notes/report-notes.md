# Report notes

## Q1: What I built + grill decisions that were MINE
- Client: Kenyon CGE study abroad blog (picked it because I'm going to DIS Copenhagen in spring).
- Overrode Claude:
  - Q3: Claude wanted "CGE staff"/"student ambassador" as words to AVOID. I kept Staff/Ambassador as the UI names (admin/editor in code).
  - Q10: Claude recommended editable slugs. I said auto-generated and NOT editable (ambassadors won't know what a slug is), frozen once published.
  - Q12: Kept the WordPress-style landing (site preview as home, sidebar tabs) instead of a plain dashboard page.
  - Spec flag 3: Claude assumed Staff drafts get deleted on deactivation like Ambassadors'. I changed it so Staff drafts are kept.
- My own additions: pending "submit for review" status, Continent→Country→Program page tree with demo data, topics on posts with a filter, footer pages (About/Contact), nav bar + breadcrumbs, ambassador drafts deleted when deactivated, "are you sure?" before delete.
- Added later as stretch: tags, search, media uploads, and a Formatting help box for students who don't know Markdown.
- Scope cuts I chose: trash/auto-delete, scheduled publishing, suggested edits, messaging/comments (all need a live server or extra features). Search was kept as a stretch ticket and later built (#10).

## Q2: Drift (what the AI made up + what caught it)
- Spec #1: Claude filled in decisions I never made (slug -2/-3 suffixes, Staff can't publish others' drafts directly, Staff drafts deleted on deactivation). Caught by reading the spec before tickets.
- T01 (#2): code showed raw role codes "admin/editor" in the UI instead of Staff/Ambassador from CONTEXT.md. Caught by /code-review. Fixed with User.role_label.
- Design passes (T11): Claude started calling posts "dispatches" in the hero, footer and headings. Not in CONTEXT.md, where the term is "Post". I caught it by reading the live site and had it changed to match the glossary.
- The admin console had never loaded its stylesheet (relative "style.css" 404'd on every nested admin page). Every ticket's tests and reviews passed anyway; it was only caught when taking the required screenshots. Fixed under its own issue, #13.
- PR #17 (media): review caught that a post could reference another post's or a draft's image ID, leaking unpublished images to the public site. Fixed before merge.

## Q3: Skills, prompts, resources
- Skills: /grill-with-docs, /to-spec, /to-tickets, /implement, /tdd, /code-review, /handoff, /setup-matt-pocock-skills

- Prompts I actually used (quote these word for word in the README):
  - Prompt 1 (grill answer A3, session 16):
    "A CGE staff member should be able to write posts as well if they desire; they should have all the tools the ambassador role has. The role names shown in the site and CONTEXT.md can be Staff and Ambassador, but in the code they stay admin (Staff) and editor (Ambassador)."
  - Prompt 2 (test seams, before /to-spec):
    "Those two seams match was I was expecting, but could you also do a third one: a small services layer for the pure rules like slug generation, the status transitions (who can move a post from a draft to pending to published and back), and what happens to an ambassadors posts when they're deactivated. Those rules are really the core of how the CGE's review works, so I want them to be tested directly as opposed to only through HTTP, and this will keep the code splits into models, routes, templates, and services."
  - How I started: the /grill-with-docs kickoff for the CGE study abroad blog (mostly drafted with help).

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
- usage_report.py after T03 (Oct 5, 5 pm):
  - T01 5% of a 5h window / 1% weekly · T02 17% / 5% · T03 15% / 2%
  - Avg ~12% of a window and 2.7% weekly per ticket, vs my plan of 30% per ticket. I overestimated by more than half.
  - T02 cost the most (four review fixes + first deploy). T03's hung review added cost too.
  - Forecast: 5 tickets need ~13% of the weekly cap, 54% remains → FITS.
- Next: trash with restore, scheduled publishing, suggested edits, private messaging, visitor accounts, search filters by views, a Preview pane for the page editor (the post editor has one). See notes/future-work.md.
- Considered adding comments, view counts, visitor accounts and private messaging after the core build, but they all need a live server. Free hosting tiers wipe the SQLite database on sleep (Render's free Postgres also expires after 30 days), and paid hosting is ~$4–5/month (Fly.io) plus the security, moderation and student-privacy responsibilities. Kept them as future work; giscus (GitHub Discussions) comments would be the cheapest first step.

## Real model failures (README needs at least 1)
- Claude ran the submission checker with the wrong Python, reported a test failure that wasn't real, then caught and corrected it.
- /setup-matt-pocock-skills skipped creating the spec/ticket/stretch labels the project needed.
- /code-review's background fork hung 36+ min (T03); Claude then reviewed its own code. Rerunning with a fresh foreground subagent fixed it.
- A /loop wakeup kept re-firing after tickets were done, re-prompting Claude for nothing.
- Claude committed T07 but didn't push, so issue #8 stayed open. Added a CLAUDE.md rule to push and confirm CLOSED.
- Claude said it couldn't take screenshots until I had it install Playwright.
- While verifying flash messages, Claude created a stray "Flash Test" account in my real local demo database instead of a test copy. It caught and deleted it before the screenshots.
- Claude (chat) told me "Add image" inserts the Markdown line for you as if it were fact before checking; I asked, and it admitted it was inferring. It turned out to be true (it appends to the end), but I had it verified before writing the help box around it.
- #13: the admin console was never styled (style.css 404) through the whole build; nobody noticed until the screenshot step.

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

## T09 (#10): site search
- T09 in the usage table = search (#10, PR #16). Search runs entirely in the browser from a JSON index built at publish time, so it works on GitHub Pages with no server.
- One T09 ledger row is a stray from a later session (Oct 8) that started before the phase label was switched, so T09's numbers (especially the 5% weekly) are only rough.

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
- Same lesson again: the admin console was unstyled the whole project and nobody, me included, noticed until the screenshot step (#13).

## Stage 1 (Oct 5)
- check_submission flagged admin templates using "/..." links (fixed), the missing mp2-mvp tag (tagged), and "secrets in history": 2 false positives inside transcripts, not real keys. Didn't rewrite history; explained it in my Stage 1 email.

## Stretch: tags (#14), search (#10, PR #16), media (#15, PR #17)

- Tags (#14): Staff-only creation; filter within a program; starter tags visa/budget/homestay/travel/classes.
- Search (#10, PR #16): scoped to a section or sitewide; Title/Text/Tags checkboxes.
- Media (#15, PR #17): post covers + images inside posts set by the author; program covers Staff-only.
- Search and media built on branches and merged through PRs instead of straight to main. I reviewed each PR and commented before merging.
  - I did this for the extra credit, and also because I wanted to look at the search changes before merging onto the main code.
- PR #17 review caught a security bug before merge: a post could reference another post's or a draft's image ID and publish it. Fixed before merging; posts can now only use images they own.
  - This showed me that even with reviews one needs to be careful. Especially with AI code and testing, the review phase needs to be extremely meticulous. 

### Images: what went wrong and what changed
- Placeholder gradient images looked like empty orange boxes; the same image showed as cover and inline; a one-card topic section was misaligned. Fixed in 7be5c67 with 7 real Wikimedia Commons photos + a Photo Credits page in the footer.
- I spotted an inline photo overflowing the post text box on the live site. Cause: no width rule on images inside posts. Fixed in 87d7603 (+ test).
- Upload check found: no resizing, only a 5 MB cap; preview hard to find after upload; cover/inline forms looked identical.
- Fixed in 690e8cc: uploads resized to max 1600px, rotated upright, EXIF/GPS location data removed, limit raised to 15 MB; returns to the image section with a thumbnail; each upload form in its own box.
 - Removing location data is a good choice for privacy reasons, especially for students studying abroad in insecure locations and situations. 

### My hands-on test (Oct 8)
- Ran the server locally; logged in as Ambassador (Jordan) and Staff (Dana); wrote, submitted, and published a post; confirmed Ambassador is refused on Users.
- Found the raw Markdown editor would confuse students who don't know Markdown.
- Added a "Formatting help" box (63a059c), open by default, "You type → You get" examples checked through the real sanitizer, tips on blank lines/spaces/moving the photo line, alt text reworded to "Describe the photo for someone who can't see it." Added to the page editor too (2e7e941). 226 tests passing.
- Asked why there's no login button on the public site: GitHub Pages has no server, so it would be a dead link (same reason as ADR-003). Decided not to add one.
  - Testing it myself was extremely helpful, allowing me to see issues that I may not have seen just through overseeing and communicating with Claude Code. I got to interact with the site as a user, and was able to give feedback from that new understanding.

## Placeholder slot
- Final usage_report.py (after the last deploy):  
  - phase          turns  5h spent   weekly  models / provider
    T01                8      5.0%     1.0%  Sonnet 5
    T02               23     17.0%     5.0%  Sonnet 5
    T03               13     15.0%     2.0%  Sonnet 5
    T04                8      9.0%     2.0%  Sonnet 5
    T05               13     12.0%     2.0%  Sonnet 5
    T06                9      8.0%     1.0%  Sonnet 5
    T07                6      7.0%     1.0%  Sonnet 5
    T08                3      5.0%     1.0%  Sonnet 5
    T09                3      2.0%     5.0%  Sonnet 5
    T10                7      4.0%     1.0%  Sonnet 5
    T11               17     94.0%    15.0%  Opus 5,Sonnet 5
    T15               14     46.0%     7.0%  Sonnet 5
    grill             14     23.0%     6.0%  Sonnet 5
    issue-13           3      8.0%     1.0%  Sonnet 5
    media              1      0.0%     0.0%  Sonnet 5
    search             1      0.0%     0.0%  Sonnet 5
    setup             14     16.0%    14.0%  Opus 5,Sonnet 5,Test
    spec               4      4.0%     1.0%  Sonnet 5
    tags              11     18.0%     3.0%  Sonnet 5
    tickets            3      4.0%     1.0%  Sonnet 5
    unlabelled        16     10.0%     2.0%  Sonnet 5

Tickets done: 12 · average weekly cost per ticket: 3.6%

- Core tickets T01–T08: 78% of one 5h window total, ~10% each, vs my plan of 30% each. 15% weekly total.
- T11 (Opus design pass): 94% of a 5h window and 15% weekly, more than all 8 core tickets combined.
- Extras cost more than the core: T15 (images + follow-ups) 46%, tags 18%, #13 8%.
- Whole project: ~307% of a 5h window (about three full windows), ~71 points of weekly cap.
- "search" and "media" show ~0% because that work was logged under other phase labels (T15/tags), same issue as the unlabelled turns.
- The final 3.6% weekly per ticket is higher than the 2.7% after T03 because it includes the design and stretch tickets.

- The Opus design pass hit my 5h limit. Opus has better design taste but burns the window much faster than Sonnet.