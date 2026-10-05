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

## Q3: Skills, prompts, resources
- Skills: /grill-with-docs, /to-spec, /to-tickets, /implement, /tdd, /code-review, /setup-matt-pocock-skills
- Prompts I actually used (need 2 quoted for README):
  - The /grill-with-docs prompt for the CGE study abroad blog
  - My test-seams answer asking for a services layer for slug, status, and deactivation rules

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

## Real model failures (README needs at least 1)
- Claude ran the submission checker with the wrong Python, reported a test failure that wasn't real, then caught and corrected it.
- /setup-matt-pocock-skills skipped creating the spec/ticket/stretch labels the project needed.

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

## Lesson
- T01's review findings were fixed and posted without me weighing in. From T02 on, I read the findings and replied in my own words on the issue.