#!/usr/bin/env python3
"""Bootstrap the CinéEstate environment files for a fresh checkout.

Why this exists
---------------
Every real key lives in a git-ignored file (`backend/.env`,
`frontend/.env.local`). That is correct — secrets must never be committed — but it
means a clone has *no* configuration at all, and the failure mode is confusing:
the UI loads, then every action fails, and it looks like the server is broken
rather than unconfigured.

This script closes that gap in one idempotent step:

1. creates ``backend/.env`` from ``backend/.env.example`` if it does not exist,
2. creates ``frontend/.env.local`` from ``frontend/.env.example`` if it does not exist,
3. makes ``API_ACCESS_KEY`` (backend) and ``NEXT_PUBLIC_API_KEY`` (frontend) the
   *same* value, generating one if neither side has it yet,
4. reports which provider keys still need filling in.

It never overwrites a file it did not create, and it never prints a key value.

Usage
-----
    python scripts/setup_env.py

Then edit ``backend/.env`` and add your provider keys.
"""

from __future__ import annotations

import argparse
import base64
import os
import secrets
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_ENV = REPO_ROOT / "backend" / ".env"
BACKEND_TEMPLATE = REPO_ROOT / "backend" / ".env.example"
FRONTEND_ENV = REPO_ROOT / "frontend" / ".env.local"
FRONTEND_TEMPLATE = REPO_ROOT / "frontend" / ".env.example"

# Keys whose presence decides whether each feature can run. Names only; this
# script never reads or echoes a value.
REQUIRED_KEYS = (
    ("GEMINI_API_KEY", "AI scene understanding (Phase 2) — required"),
    ("MAGIC_HOUR_API_KEY", "Magic Hour generative video — optional, no public URL needed"),
    ("JSON2VIDEO_API_KEY", "JSON2Video cloud renderer — optional, needs PUBLIC_BASE_URL"),
    ("VIDEO_API_KEY", "Google Veo — optional, hardest free tier"),
)


def parse_env(path: Path) -> dict:
    """Minimal dotenv reader: KEY=VALUE, ignoring comments and blanks."""
    values = {}
    if not path.is_file():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def upsert(path: Path, key: str, value: str) -> bool:
    """Sets KEY=value in place, appending if absent. Returns True if changed."""
    lines = path.read_text(encoding="utf-8").splitlines()
    prefix = f"{key}="
    for i, raw in enumerate(lines):
        if raw.strip().startswith(prefix):
            if raw.strip() == f"{key}={value}":
                return False
            lines[i] = f"{key}={value}"
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            return True
    lines.append(f"{key}={value}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return True


def generate_key() -> str:
    """A URL-safe secret that survives .env, shell and JSON quoting untouched."""
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("=")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--rotate-key",
        action="store_true",
        help="Generate a NEW shared access key even if one already exists.",
    )
    args = parser.parse_args()

    print("CinéEstate — environment setup")
    print(f"Repository: {REPO_ROOT}\n")

    # 1. Create missing files from their templates.
    for target, template in (
        (BACKEND_ENV, BACKEND_TEMPLATE),
        (FRONTEND_ENV, FRONTEND_TEMPLATE),
    ):
        if target.is_file():
            print(f"  keep    {target.relative_to(REPO_ROOT)} (already exists)")
            continue
        if not template.is_file():
            print(f"  ERROR   missing template {template.relative_to(REPO_ROOT)}", file=sys.stderr)
            return 1
        target.write_text(template.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"  create  {target.relative_to(REPO_ROOT)} (from {template.name})")

    # 2. Both sides must share one access key, or every request is a 401.
    backend_values = parse_env(BACKEND_ENV)
    frontend_values = parse_env(FRONTEND_ENV)

    backend_key = backend_values.get("API_ACCESS_KEY", "")
    frontend_key = frontend_values.get("NEXT_PUBLIC_API_KEY", "")

    if args.rotate_key:
        shared_key = generate_key()
        origin = "rotated on request"
    elif backend_key:
        shared_key = backend_key
        origin = "reused from backend/.env"
    elif frontend_key:
        shared_key = frontend_key
        origin = "reused from frontend/.env.local"
    else:
        shared_key = generate_key()
        origin = "newly generated"

    backend_changed = upsert(BACKEND_ENV, "API_ACCESS_KEY", shared_key)
    frontend_changed = upsert(FRONTEND_ENV, "NEXT_PUBLIC_API_KEY", shared_key)

    print(f"\n  shared access key ({origin}, {len(shared_key)} chars):")
    print(f"    API_ACCESS_KEY        {'updated in backend/.env' if backend_changed else 'already in sync'}")
    print(f"    NEXT_PUBLIC_API_KEY   {'updated in frontend/.env.local' if frontend_changed else 'already in sync'}")
    if backend_changed or frontend_changed:
        print("    Both sides now hold the SAME value. Never commit either file.")

    # 3. Keep the frontend pointed at the backend.
    if upsert(FRONTEND_ENV, "NEXT_PUBLIC_API_URL", "http://localhost:8000"):
        print("    NEXT_PUBLIC_API_URL   set to http://localhost:8000")

    # 4. Report what is still missing. Names only.
    print("\nProvider keys in backend/.env:")
    backend_values = parse_env(BACKEND_ENV)
    missing = []
    for key, purpose in REQUIRED_KEYS:
        if backend_values.get(key):
            print(f"  [x] {key}")
        else:
            print(f"  [ ] {key:<22} {purpose}")
            missing.append(key)

    print("\nNotes:")
    print("  * The backend loads .env relative to the BACKEND package, so it works")
    print("    whether you launch uvicorn from the repository root or from backend/.")
    print("  * NEXT_PUBLIC_* values are inlined at build time: restart `next dev`")
    print("    (and rebuild on Vercel) after changing them.")
    print("  * With no provider key at all the app still runs — clips are rendered")
    print("    locally by the cinematic Ken Burns engine, with no quota.")

    if missing:
        print("\nNext: open backend/.env and fill in the keys listed with [ ] above.")
    else:
        print("\nAll provider keys are present. Run `python scripts/check_config.py` to verify.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
