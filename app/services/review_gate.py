"""The Post review-gate state machine (ADR-004) — pure, no FastAPI or SQLite
dependency. Every cell of the spec's status/action table, including the
disallowed ones, lives here so app/routes/posts.py only has to call
`transition()` and turn a ValueError into a 403.

| From      | Action    | Who                        | To        |
|-----------|-----------|-----------------------------|-----------|
| draft     | submit    | the Post's own author       | pending   |
| pending   | publish   | any admin                   | published |
| pending   | bounce    | any admin                   | draft     |
| draft     | publish   | admin, own Post only        | published |
| published | unpublish | any admin                   | draft     |

No other (status, action) pair exists.
"""
from __future__ import annotations

from typing import Callable

_Rule = Callable[[str, bool], bool]

_RULES: dict[tuple[str, str], _Rule] = {
    ("draft", "submit"): lambda role, is_author: is_author,
    ("draft", "publish"): lambda role, is_author: role == "admin" and is_author,
    ("pending", "publish"): lambda role, is_author: role == "admin",
    ("pending", "bounce"): lambda role, is_author: role == "admin",
    ("published", "unpublish"): lambda role, is_author: role == "admin",
}

_TARGETS: dict[tuple[str, str], str] = {
    ("draft", "submit"): "pending",
    ("draft", "publish"): "published",
    ("pending", "publish"): "published",
    ("pending", "bounce"): "draft",
    ("published", "unpublish"): "draft",
}

ACTION_LABELS = {
    "submit": "Submit for review",
    "publish": "Publish",
    "bounce": "Bounce to draft",
    "unpublish": "Unpublish",
}


def transition(status: str, action: str, role: str, is_author: bool) -> str:
    """Return the Post's new status.

    Raises ValueError if `action` isn't allowed from `status` for this
    role/authorship combination — including an admin trying to take someone
    else's draft straight to published, which must pass through pending
    first same as anyone's.
    """
    key = (status, action)
    rule = _RULES.get(key)
    if rule is None or not rule(role, is_author):
        raise ValueError(
            f"{action!r} is not allowed on a {status!r} post "
            f"(role={role!r}, is_author={is_author!r})"
        )
    return _TARGETS[key]


def available_actions(status: str, role: str, is_author: bool) -> list[str]:
    """Actions this role/authorship combination may currently take from
    `status` — used to decide which buttons to render in the Posts list."""
    return [
        action
        for (st, action), rule in _RULES.items()
        if st == status and rule(role, is_author)
    ]
