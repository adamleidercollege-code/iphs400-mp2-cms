# Future work

Features worth building later, deliberately not in this build, and why —
separate from `docs/adr/`, because neither of these is a hard architectural
trade-off this project is locking in; they're just not worth their cost here.

## Trash with restore and a 30-day auto-delete

Field note 8: WordPress sends a deleted Post/Page to a trash instead of
removing it, then purges it automatically after a configurable delay. Doing
the auto-purge half properly needs something running in the background to
check ages and clear old entries on a schedule — and the admin console here
only runs when someone has it open (`uv run cms serve`), with nothing
scheduled in between. A trash *without* the auto-purge is just a delayed,
confusing delete, so it's not worth building half the feature.

For now: plain delete, with an "are you sure?" confirmation before it runs
(decided alongside this), so CGE doesn't lose a Post by accident — but once
deleted, it's gone.

## Scheduled / visibility-gated publish

Field note 3: WordPress's publish dialog lets you set a future publish date
and public/private visibility. The draft → pending → published status
already gives CGE a manual visibility gate (see `CONTEXT.md`). A *scheduled*
future-dated auto-publish needs something to flip the status at the right
time with nobody watching — which this project doesn't have (`cms publish`
is a manual, one-way step, ADR-001). A date field that doesn't actually
schedule anything would look like it works and doesn't, which is worse than
not having it.

For now: if CGE wants a Post live on a specific day, they publish it that
day.
