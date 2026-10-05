# ADR-004: Posts get a third status, pending, between draft and published

**Status:** accepted
**Date:** 2026-10-04

## Context

The manual's capability 3 names only draft/published for Posts. The client's
hard constraint — an ambassador must never publish without CGE review — can
be met with just those two states if "draft" simply means "admin hasn't
promoted this yet" and the ambassador never controls a publish action. But
the client specifically wants an explicit submit-for-review step: an
ambassador finishes writing, hands it off, and loses edit access the moment
they do, before any admin has looked at it. A two-state model has no status
for "done writing, waiting on a decision, locked" — that is a third state.

## Decision

Post status is draft → pending → published. An ambassador can create, edit,
and delete their own Post only while it is draft. Submitting moves it to
pending, which locks it from the author. An admin reviewing a pending Post
either publishes it or bounces it back to draft for more edits. Only an admin
can move a Post into or out of published.

## Consequences

- Every Post list, filter, and permission check in the codebase treats
  pending as its own case — not as a synonym for draft (it is not
  author-editable) or published (it is not public).
- "Nothing unapproved reaches the public site" is enforced by restricting the
  publish transition to admins, not by the pending state itself; pending is
  what makes the hand-off visible and locks the author out while it waits.
- The manual's own capability list says draft/published; this is a deliberate
  extension to meet the client's explicit review-gate request, not a
  deviation from what was asked for, and a future reader should expect three
  Post statuses despite that wording.

## Why this is an ADR

Hard to reverse: every status check, once built, assumes three states.
Surprising without context: the manual itself only names two. Genuine
trade-off: two states is simpler and still meets the letter of capability 3,
but three is what the client's actual review workflow needs.
