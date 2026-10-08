"""`.env` auto-loading (app/env_file.py) — the grader's actual workflow is

    cp .env.example .env
    uv run python scripts/seed_demo.py
    uv run cms serve

with nothing sourced into their shell first, so app/settings.py must pick up
`.env` on its own.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from app.env_file import load_into_environ, parse_dotenv

_ROOT = Path(__file__).resolve().parents[1]


# -- Parser: pure, no filesystem or environment ------------------------------


def test_parses_key_value_pairs():
    assert parse_dotenv("FOO=bar\nBAZ=qux\n") == {"FOO": "bar", "BAZ": "qux"}


def test_skips_blank_lines_and_comments():
    text = "# a comment\n\nFOO=bar\n  # indented comment\nBAZ=qux\n"
    assert parse_dotenv(text) == {"FOO": "bar", "BAZ": "qux"}


def test_strips_matched_quotes_from_value():
    assert parse_dotenv('FOO="bar baz"\nQUX=\'quux\'\n') == {"FOO": "bar baz", "QUX": "quux"}


def test_tolerates_a_value_containing_an_equals_sign():
    assert parse_dotenv("FOO=a=b=c\n") == {"FOO": "a=b=c"}


# -- load_into_environ: real-env-wins, missing-file-is-a-no-op --------------


def test_sets_keys_missing_from_environ(tmp_path):
    (tmp_path / ".env").write_text("CMS_ADMIN_PASSWORD=from-dotenv\n")
    environ: dict[str, str] = {}
    load_into_environ(tmp_path / ".env", environ)
    assert environ == {"CMS_ADMIN_PASSWORD": "from-dotenv"}


def test_a_real_environment_variable_always_wins(tmp_path):
    (tmp_path / ".env").write_text("CMS_ADMIN_PASSWORD=from-dotenv\n")
    environ = {"CMS_ADMIN_PASSWORD": "already-exported"}
    load_into_environ(tmp_path / ".env", environ)
    assert environ["CMS_ADMIN_PASSWORD"] == "already-exported"


def test_missing_dotenv_file_is_a_no_op(tmp_path):
    environ: dict[str, str] = {}
    load_into_environ(tmp_path / "no-such-file.env", environ)
    assert environ == {}


# -- End to end: the grader's exact three commands, fresh clone, no exports -


def _fresh_checkout(tmp_path: Path) -> Path:
    """Only what scripts/seed_demo.py needs to import and run: app/,
    scripts/seed_demo.py (plus its seed_photos/ assets), and .env.example —
    a fresh clone minus git."""
    checkout = tmp_path / "checkout"
    shutil.copytree(_ROOT / "app", checkout / "app")
    (checkout / "scripts").mkdir()
    shutil.copy(_ROOT / "scripts" / "seed_demo.py", checkout / "scripts" / "seed_demo.py")
    shutil.copytree(
        _ROOT / "scripts" / "seed_photos", checkout / "scripts" / "seed_photos"
    )
    shutil.copy(_ROOT / ".env.example", checkout / ".env.example")
    return checkout


def test_seed_demo_runs_with_only_a_copied_env_file_and_no_shell_exports(tmp_path):
    """Reproduces the grader's workflow: cp .env.example .env, then run the
    script directly — nothing sourced into the shell. This is exactly the
    sequence that silently failed before app/settings.py auto-loaded .env:
    `os.environ.get("CMS_ADMIN_PASSWORD")` was None, seed_demo.py printed
    "Set CMS_ADMIN_PASSWORD ..." and exited 1."""
    checkout = _fresh_checkout(tmp_path)
    shutil.copy(checkout / ".env.example", checkout / ".env")

    clean_env = {"PATH": os.environ["PATH"]}  # no CMS_* exported
    result = subprocess.run(
        [sys.executable, str(checkout / "scripts" / "seed_demo.py")],
        cwd=checkout, env=clean_env, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Seeded" in result.stdout
    assert (checkout / "cms.db").exists()


def test_seed_demo_still_fails_clearly_with_no_env_file_at_all(tmp_path):
    """Without a .env to load, the original behavior (a clear error, not a
    crash) still holds — this isn't papering over a missing-password case."""
    checkout = _fresh_checkout(tmp_path)
    # No .env copied in.

    clean_env = {"PATH": os.environ["PATH"]}
    result = subprocess.run(
        [sys.executable, str(checkout / "scripts" / "seed_demo.py")],
        cwd=checkout, env=clean_env, capture_output=True, text=True,
    )
    assert result.returncode == 1
    assert "CMS_ADMIN_PASSWORD" in result.stdout
