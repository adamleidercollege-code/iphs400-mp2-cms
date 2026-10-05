"""T04: Posts — the review-gate state machine (ADR-004)."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from app import models
from app.services import review_gate
from tests.conftest import _csrf_token_from

_ROOT = Path(__file__).resolve().parents[1]

STATUSES = ["draft", "pending", "published"]
ACTIONS = ["submit", "publish", "bounce", "unpublish"]

# Every (status, action, role, is_author) -> expected target status, or None
# if the transition must be rejected. This is every cell of the spec's table,
# including every disallowed combination.
CASES: list[tuple[str, str, str, bool, str | None]] = [
    # draft --submit--> pending: the Post's own author, any role.
    ("draft", "submit", "editor", True, "pending"),
    ("draft", "submit", "admin", True, "pending"),
    ("draft", "submit", "editor", False, None),  # another Ambassador's draft
    ("draft", "submit", "admin", False, None),  # admin isn't the author
    # draft --publish (self-publish)--> published: admin, own Post only.
    ("draft", "publish", "admin", True, "published"),
    ("draft", "publish", "admin", False, None),  # someone else's draft
    ("draft", "publish", "editor", True, None),  # editor can never publish
    ("draft", "publish", "editor", False, None),
    # pending --publish--> published: any admin, regardless of author.
    ("pending", "publish", "admin", True, "published"),
    ("pending", "publish", "admin", False, "published"),
    ("pending", "publish", "editor", True, None),
    ("pending", "publish", "editor", False, None),
    # pending --bounce--> draft: any admin, regardless of author.
    ("pending", "bounce", "admin", True, "draft"),
    ("pending", "bounce", "admin", False, "draft"),
    ("pending", "bounce", "editor", True, None),
    ("pending", "bounce", "editor", False, None),
    # published --unpublish--> draft: any admin, regardless of author.
    ("published", "unpublish", "admin", True, "draft"),
    ("published", "unpublish", "admin", False, "draft"),
    ("published", "unpublish", "editor", True, None),
    ("published", "unpublish", "editor", False, None),
    # No other (status, action) pair exists at all.
    ("draft", "bounce", "admin", True, None),
    ("draft", "unpublish", "admin", True, None),
    ("pending", "submit", "editor", True, None),
    ("pending", "unpublish", "admin", True, None),
    ("published", "submit", "editor", True, None),
    ("published", "bounce", "admin", True, None),
]


@pytest.mark.parametrize("status,action,role,is_author,expected", CASES)
def test_transition_table(status, action, role, is_author, expected):
    if expected is None:
        with pytest.raises(ValueError):
            review_gate.transition(status, action, role, is_author)
    else:
        assert review_gate.transition(status, action, role, is_author) == expected


@pytest.mark.parametrize("status", STATUSES)
@pytest.mark.parametrize("role", ["admin", "editor"])
@pytest.mark.parametrize("is_author", [True, False])
def test_available_actions_matches_transition_table(status, role, is_author):
    """available_actions() must agree with transition() for every action,
    not just the ones CASES happens to spell out disallowed combos for."""
    allowed = review_gate.available_actions(status, role, is_author)
    for action in ACTIONS:
        try:
            expected_target = review_gate.transition(status, action, role, is_author)
        except ValueError:
            assert action not in allowed
        else:
            assert action in allowed
            # available_actions must not have side effects or disagree on the target.
            assert review_gate.transition(status, action, role, is_author) == expected_target


# --- HTTP seam: the routes wire the above into the Posts admin screens -----


def _load_seed_demo():
    """scripts/ isn't a package (see tests/test_usage_report.py for prior art)."""
    spec = importlib.util.spec_from_file_location(
        "seed_demo", _ROOT / "scripts" / "seed_demo.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _seed_program(parent_author_id: int) -> models.Page:
    home = models.ensure_home_page()
    continent = models.create_page(home.id, "Asia", "", False, parent_author_id)
    country = models.create_page(continent.id, "Japan", "", False, parent_author_id)
    return models.create_page(country.id, "Kyoto Exchange", "", False, parent_author_id)


def _create_draft_post(c, program_id: int, title: str = "My First Week") -> models.Post:
    page = c.get(f"/admin/posts/new?program_id={program_id}")
    token = _csrf_token_from(page.text)
    c.post(
        "/admin/posts/new",
        data={"program_id": str(program_id), "title": title, "body": "Hello",
              "topic": "housing", "action": "save", "csrf_token": token},
        follow_redirects=False,
    )
    return models.list_posts_by_program(program_id)[0]


def test_ambassador_submits_own_draft_then_loses_edit_access(client_as):
    c = client_as("editor")
    admin = models.get_user_by_email("admin@example.test")
    program = _seed_program(admin.id)
    post = _create_draft_post(c, program.id)

    list_page = c.get(f"/admin/posts?program_id={program.id}")
    token = _csrf_token_from(list_page.text)
    response = c.post(f"/admin/posts/{post.id}/submit",
                       data={"csrf_token": token}, follow_redirects=False)
    assert response.status_code == 303
    assert models.get_post_by_id(post.id).status == "pending"

    # Locked out of editing now that it's pending.
    assert c.get(f"/admin/posts/{post.id}/edit").status_code == 403


def test_staff_publishes_or_bounces_a_pending_post_from_anyone(client_as):
    admin_c = client_as("admin")
    admin = models.get_user_by_email("admin@example.test")
    program = _seed_program(admin.id)

    editor_c = client_as("editor")
    post = _create_draft_post(editor_c, program.id)
    token = _csrf_token_from(editor_c.get(f"/admin/posts?program_id={program.id}").text)
    editor_c.post(f"/admin/posts/{post.id}/submit", data={"csrf_token": token})
    assert models.get_post_by_id(post.id).status == "pending"

    token = _csrf_token_from(admin_c.get(f"/admin/posts?program_id={program.id}").text)
    response = admin_c.post(f"/admin/posts/{post.id}/bounce",
                             data={"csrf_token": token}, follow_redirects=False)
    assert response.status_code == 303
    assert models.get_post_by_id(post.id).status == "draft"

    # Resubmit, then publish this time.
    token = _csrf_token_from(editor_c.get(f"/admin/posts?program_id={program.id}").text)
    editor_c.post(f"/admin/posts/{post.id}/submit", data={"csrf_token": token})
    token = _csrf_token_from(admin_c.get(f"/admin/posts?program_id={program.id}").text)
    response = admin_c.post(f"/admin/posts/{post.id}/publish",
                             data={"csrf_token": token}, follow_redirects=False)
    assert response.status_code == 303
    assert models.get_post_by_id(post.id).status == "published"


def test_staff_self_publishes_own_draft_directly(client_as):
    admin_c = client_as("admin")
    admin = models.get_user_by_email("admin@example.test")
    program = _seed_program(admin.id)
    post = _create_draft_post(admin_c, program.id)

    token = _csrf_token_from(admin_c.get(f"/admin/posts?program_id={program.id}").text)
    response = admin_c.post(f"/admin/posts/{post.id}/publish",
                             data={"csrf_token": token}, follow_redirects=False)
    assert response.status_code == 303
    assert models.get_post_by_id(post.id).status == "published"


def test_staff_unpublishes_a_live_post(client_as):
    admin_c = client_as("admin")
    admin = models.get_user_by_email("admin@example.test")
    program = _seed_program(admin.id)
    post = _create_draft_post(admin_c, program.id)
    token = _csrf_token_from(admin_c.get(f"/admin/posts?program_id={program.id}").text)
    admin_c.post(f"/admin/posts/{post.id}/publish", data={"csrf_token": token})

    token = _csrf_token_from(admin_c.get(f"/admin/posts?program_id={program.id}").text)
    response = admin_c.post(f"/admin/posts/{post.id}/unpublish",
                             data={"csrf_token": token}, follow_redirects=False)
    assert response.status_code == 303
    assert models.get_post_by_id(post.id).status == "draft"


def test_admin_cannot_push_someone_elses_draft_straight_to_published(client_as):
    admin_c = client_as("admin")
    admin = models.get_user_by_email("admin@example.test")
    program = _seed_program(admin.id)

    editor_c = client_as("editor")
    post = _create_draft_post(editor_c, program.id)

    token = _csrf_token_from(admin_c.get(f"/admin/posts?program_id={program.id}").text)
    response = admin_c.post(f"/admin/posts/{post.id}/publish",
                             data={"csrf_token": token}, follow_redirects=False)
    assert response.status_code == 403
    assert models.get_post_by_id(post.id).status == "draft"


def test_ambassador_rejected_for_any_transition_other_than_submitting_own_draft(client_as):
    admin = models.get_user_by_email("admin@example.test")
    program = _seed_program(admin.id)

    owner = client_as("editor")
    post = _create_draft_post(owner, program.id)

    other = models.create_user(
        email="other-editor@example.test", password="test-other-pw",
        role="editor", display_name="Other Ambassador",
    )
    intruder = client_as("editor")
    login_page = intruder.get("/login")
    token = _csrf_token_from(login_page.text)
    intruder.post("/login", data={"email": other.email, "password": "test-other-pw",
                                   "csrf_token": token})

    token = _csrf_token_from(owner.get(f"/admin/posts?program_id={program.id}").text)
    assert intruder.post(f"/admin/posts/{post.id}/submit",
                          data={"csrf_token": token}).status_code == 403
    assert intruder.post(f"/admin/posts/{post.id}/publish",
                          data={"csrf_token": token}).status_code == 403
    assert intruder.post(f"/admin/posts/{post.id}/bounce",
                          data={"csrf_token": token}).status_code == 403
    assert intruder.post(f"/admin/posts/{post.id}/unpublish",
                          data={"csrf_token": token}).status_code == 403
    assert models.get_post_by_id(post.id).status == "draft"


def test_set_post_status_rejects_a_stale_from_status(client_as):
    """models.set_post_status guards every write with WHERE status =
    from_status, so a second writer working off a stale read (e.g. two
    admins racing to act on the same pending Post) gets a conflict instead
    of silently clobbering the first writer's transition."""
    admin_c = client_as("admin")
    admin = models.get_user_by_email("admin@example.test")
    program = _seed_program(admin.id)
    post = _create_draft_post(admin_c, program.id)
    models.set_post_status(post.id, from_status="draft", to_status="pending")

    with pytest.raises(models.StatusConflict):
        models.set_post_status(post.id, from_status="draft", to_status="published")

    # The stale write made no change.
    assert models.get_post_by_id(post.id).status == "pending"


def test_unpublish_clears_published_at(client_as):
    admin_c = client_as("admin")
    admin = models.get_user_by_email("admin@example.test")
    program = _seed_program(admin.id)
    post = _create_draft_post(admin_c, program.id)
    models.set_post_status(post.id, from_status="draft", to_status="published")
    assert models.get_post_by_id(post.id).published_at is not None

    models.set_post_status(post.id, from_status="published", to_status="draft")
    assert models.get_post_by_id(post.id).published_at is None


def test_seed_demo_seeds_posts_in_all_three_statuses(client):
    seed_demo = _load_seed_demo()
    admin = models.get_user_by_email("admin@example.test")
    editor = models.get_user_by_email("editor@example.test")
    programs = seed_demo._seed_pages(admin.id)
    seed_demo._seed_posts(programs, editor.id)

    all_posts = [p for program in programs for p in models.list_posts_by_program(program.id)]
    assert len(all_posts) == len(programs)
    assert {p.status for p in all_posts} == {"draft", "pending", "published"}
    assert len({p.topic for p in all_posts}) > 1
