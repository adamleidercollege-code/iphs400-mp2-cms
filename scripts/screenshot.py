#!/usr/bin/env python3
"""Screenshot pages with Playwright, for the design-review passes T11+ ask for.

    uv run python scripts/screenshot.py --out notes/screenshots \\
        --widths 1280 390 \\
        --path / home \\
        --path /asia/ asia

Starts the real app (`app.main:app`) on a throwaway port, waits for it to
come up, then drives headless Chromium to capture each --path at each
--width as "<name>-<width>.png" under --out. Pass --login EMAIL PASSWORD to
authenticate first (needed for admin screenshots).
"""
from __future__ import annotations

import argparse
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for(url: str, timeout: float = 15.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(url, timeout=1)
            return
        except OSError:
            time.sleep(0.2)
    raise RuntimeError(f"server never came up at {url}")


def _login(page, base: str, email: str, password: str) -> None:
    page.goto(base + "/login", wait_until="networkidle")
    token = page.get_attribute('input[name="csrf_token"]', "value")
    page.fill('input[name="email"]', email)
    page.fill('input[name="password"]', password)
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")
    if token is None:
        raise RuntimeError("login page had no csrf_token field")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--widths", nargs="+", type=int, default=[1280, 390])
    parser.add_argument(
        "--path", nargs=2, action="append", metavar=("URL_PATH", "NAME"),
        default=[], dest="paths", help="repeatable: a URL path and a filename stem",
    )
    parser.add_argument(
        "--login", nargs=2, metavar=("EMAIL", "PASSWORD"), default=None,
        help="log in with these creds before screenshotting",
    )
    args = parser.parse_args(argv)

    if not args.paths:
        parser.error("pass at least one --path URL_PATH NAME")

    args.out.mkdir(parents=True, exist_ok=True)
    port = _free_port()
    base = f"http://127.0.0.1:{port}"

    server = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port)],
        cwd=ROOT,
    )
    try:
        _wait_for(base + "/")
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for width in args.widths:
                context = browser.new_context(viewport={"width": width, "height": 900})
                page = context.new_page()
                if args.login:
                    _login(page, base, *args.login)
                for url_path, name in args.paths:
                    page.goto(base + url_path, wait_until="networkidle")
                    page.screenshot(path=str(args.out / f"{name}-{width}.png"), full_page=True)
                context.close()
            browser.close()
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=10)

    print(f"Saved screenshots to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
