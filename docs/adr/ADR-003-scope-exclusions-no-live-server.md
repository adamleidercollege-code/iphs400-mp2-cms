# ADR-003: Messaging, visitor accounts, an IT role, usage-based filters, and suggested edits are out of scope

**Status:** accepted
**Date:** 2026-10-04

## Context

The client brief's "What I'd add next" section lists private messaging, a
visitor/commenter account role, an IT/developer role, and search filters based
on view/comment counts — and says outright that messaging and the usage
filters "need a live server." ADR-001 already fixed the admin console as
local-only and the public site as a static export. Separately, while settling
the review workflow (ADR-004), built-in "suggested edits" — a way for an admin
to leave an inline revision request on a bounced Post rather than talking to
the ambassador outside the CMS — came up and was rejected for the same reason:
it is more review tooling than this build needs.

## Decision

None of these five ship in this build: private messaging, a visitor/commenter
role, an IT/developer role, view/comment-based search filters, and in-CMS
suggested-edit tooling. When CGE bounces a pending Post back to draft, or a
student wants to ask a follow-up question, that happens outside the CMS
(email, in person) — the same channels that already exist today.

## Consequences

- Students keep reaching ambassadors and CGE the way they already do; the
  brief itself says this "covers most of what messaging would do."
- The review loop stays simple: bouncing pending → draft stores no reason and
  starts no thread anywhere in the data model.
- Revisiting messaging or usage-based counters later is an architecture
  change (a live server), not a feature add — budget for it as the former.

## Why this is an ADR

Hard to reverse: adding a live server later reopens ADR-001's whole
local-admin/static-public shape. Surprising without context: the brief itself
asks for these, so a reader needs to know they were deliberately deferred, not
missed. Genuine trade-off: static-site simplicity and the laptop-only security
story, against functionality the client explicitly wants eventually.
