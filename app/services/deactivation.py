"""The deactivation cascade (spec's Deactivation cascade section, CONTEXT.md's
Status entry) — pure, no FastAPI or SQLite dependency: given a user's role,
decide whether their draft content should be deleted on deactivation.
"""
from __future__ import annotations


def should_delete_drafts(role: str) -> bool:
    """Ambassador (editor) drafts are deleted on deactivation — nothing worth
    keeping from a student who's left. Staff (admin) drafts are left exactly
    as they are; any other Staff member can already view, edit, publish, or
    delete them like any other content. Pending and published content is
    never touched, regardless of role — this only decides drafts.
    """
    return role == "editor"
