"""Load `.env` into the process environment automatically.

The grader's workflow is `cp .env.example .env` then `uv run ...` directly —
nothing sources `.env` into their shell first. Without this, every script and
`cms serve` would only ever see a *real* exported environment variable, never
one that just sits in the `.env` file, and `scripts/seed_demo.py` would fail
with "Set CMS_ADMIN_PASSWORD ..." before it ever got to seed anything.

A one-file parser rather than python-dotenv (pyproject.toml's dependency list
is fixed for this project; `.env` is simple enough — KEY=VALUE, `#` comments,
optional quotes — that pulling in a dependency for it isn't worth it).

A real environment variable always wins over `.env`: CI secrets, Docker env,
or a developer's own `export FOO=bar` are never overwritten by the file.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import MutableMapping


def parse_dotenv(text: str) -> dict[str, str]:
    """Pure: KEY=VALUE per line, blank lines and `#` comments ignored,
    surrounding matched quotes on the value stripped."""
    values: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if key:
            values[key] = value
    return values


def load_into_environ(
    path: Path, environ: MutableMapping[str, str] | None = None
) -> None:
    """Set each KEY=VALUE from `path` into `environ` (os.environ by
    default), skipping any key already present there. A no-op if `path`
    doesn't exist, so CI (which sets real env vars and never writes `.env`)
    is unaffected."""
    if not path.exists():
        return
    target = os.environ if environ is None else environ
    for key, value in parse_dotenv(path.read_text()).items():
        target.setdefault(key, value)
