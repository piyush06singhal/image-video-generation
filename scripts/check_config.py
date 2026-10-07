#!/usr/bin/env python3
"""Diagnose a CinéEstate configuration without printing a single secret value.

The painful failure this exists to catch:

    "It runs on my machine, but the API keys do nothing on my friend's."

Almost always one of:

* no ``backend/.env`` at all — it is git-ignored, so a fresh clone has none,
* ``API_ACCESS_KEY`` set on one side and not the other, so every call is a 401,
* template placeholders (``your_gemini_api_key_here``) never replaced,
* the backend started from a directory where it could not find its ``.env``.

Every check prints names, booleans and short SHA-256 fingerprints — never values —
so the output is safe to paste into a bug report.

Usage
-----
    python scripts/check_config.py
    python scripts/check_config.py --url https://your-backend.vercel.app
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_ENV = REPO_ROOT / "backend" / ".env"
FRONTEND_ENV = REPO_ROOT / "frontend" / ".env.local"

PLACEHOLDERS = {
    "",
    "your_gemini_api_key_here",
    "your_key",
    "changeme",
    "replace_me",
}

PROBLEMS: list[str] = []
NOTES: list[str] = []


def parse_env(path: Path) -> dict:
    values: dict = {}
    if not path.is_file():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def fingerprint(value: str) -> str:
    """First 8 hex chars of the SHA-256. Confirms a match without revealing it."""
    return hashlib.sha256(value.encode()).hexdigest()[:8]


def ok(msg: str) -> None:
    print(f"  \033[32mPASS\033[0m  {msg}")


def warn(msg: str) -> None:
    print(f"  \033[33mWARN\033[0m  {msg}")
    NOTES.append(msg)


def fail(msg: str) -> None:
    print(f"  \033[31mFAIL\033[0m  {msg}")
    PROBLEMS.append(msg)


def section(title: str) -> None:
    print(f"\n{title}")


def check_files() -> tuple:
    section("1. Environment files")
    backend_values = parse_env(BACKEND_ENV)
    frontend_values = parse_env(FRONTEND_ENV)

    for label, path, values in (
        ("backend/.env", BACKEND_ENV, backend_values),
        ("frontend/.env.local", FRONTEND_ENV, frontend_values),
    ):
        if path.is_file() and values:
            ok(f"{label} exists and parses ({len(values)} settings)")
        elif path.is_file():
            fail(f"{label} exists but is empty — copy the .env.example template")
        else:
            fail(f"{label} is missing — run `python scripts/setup_env.py`")

    for label, path in (("backend/.env", BACKEND_ENV), ("frontend/.env.local", FRONTEND_ENV)):
        if path.is_file() and "[TEMPLATE]" in path.read_text(encoding="utf-8"):
            fail(f"{label} still contains a leftover [TEMPLATE] marker line")

    return backend_values, frontend_values


def check_api_key(backend_values: dict, frontend_values: dict) -> None:
    section("2. Shared API access key (the usual cross-machine culprit)")
    backend_key = backend_values.get("API_ACCESS_KEY", "")
    frontend_key = frontend_values.get("NEXT_PUBLIC_API_KEY", "")

    print(f"  API_ACCESS_KEY      (backend)  : {'set' if backend_key else 'unset'}"
          + (f"  fp={fingerprint(backend_key)}" if backend_key else ""))
    print(f"  NEXT_PUBLIC_API_KEY (frontend) : {'set' if frontend_key else 'unset'}"
          + (f"  fp={fingerprint(frontend_key)}" if frontend_key else ""))

    if not backend_key and not frontend_key:
        ok("Neither side sets a key, so the API is open. Fine for localhost only.")
        warn("Anyone who can reach the backend can spend your provider quota. Set a key "
             "before exposing it through a tunnel or deploying it.")
        return
    if backend_key and not frontend_key:
        fail("The backend requires a key but the frontend sends none: every request "
             "will be 401. Set NEXT_PUBLIC_API_KEY in frontend/.env.local to the same "
             "value as API_ACCESS_KEY, then restart `next dev`.")
        return
    if frontend_key and not backend_key:
        fail("The frontend sends a key the backend does not expect. Copy the value into "
             "API_ACCESS_KEY in backend/.env and restart the backend.")
        return
    if backend_key == frontend_key:
        ok(f"Both sides hold the same key (fp={fingerprint(backend_key)}).")
    else:
        fail("The two keys differ, so every request will be 401. Re-run "
             "`python scripts/setup_env.py` to sync them.")


def check_providers(backend_values: dict) -> None:
    section("3. Provider credentials")
    placeholders_found = []
    for key, purpose in (
        ("GEMINI_API_KEY", "AI scene understanding"),
        ("MAGIC_HOUR_API_KEY", "Magic Hour generative video"),
        ("JSON2VIDEO_API_KEY", "JSON2Video cloud renderer"),
        ("VIDEO_API_KEY", "Google Veo"),
    ):
        value = backend_values.get(key, "")
        if value in PLACEHOLDERS:
            print(f"  --    {key:<22} unset ({purpose} unavailable)")
        elif value.lower() in PLACEHOLDERS or "your_" in value.lower():
            fail(f"{key} still holds the template placeholder, not a real key")
            placeholders_found.append(key)
        else:
            ok(f"{key:<22} set (fp={fingerprint(value)})")

    if backend_values.get("JSON2VIDEO_API_KEY") and not backend_values.get("PUBLIC_BASE_URL"):
        warn("JSON2VIDEO_API_KEY is set but PUBLIC_BASE_URL is empty, so JSON2Video "
             "cannot fetch the source photos and is skipped in `auto` mode. Either set "
             "PUBLIC_BASE_URL to a publicly reachable origin, or remove the key.")

    if not any(
        backend_values.get(k)
        for k in ("MAGIC_HOUR_API_KEY", "JSON2VIDEO_API_KEY", "VIDEO_API_KEY", "GEMINI_API_KEY")
    ):
        warn("No video provider key is configured. Everything still works, but clips "
             "come from the local Ken Burns renderer only.")


def check_backend_settings() -> None:
    section("4. What the backend actually loads")
    venv_python = REPO_ROOT / "backend" / "venv" / "bin" / "python"
    python = str(venv_python) if venv_python.is_file() else sys.executable

    code = (
        "import json, sys; sys.path.insert(0, '.');"
        "from app.core.config import settings;"
        "from app.services.video_generation.factory import resolve_video_provider_name;"
        "r = settings.configuration_report();"
        "r['video_provider'] = resolve_video_provider_name();"
        "print(json.dumps(r))"
    )
    try:
        proc = subprocess.run(
            [python, "-c", code],
            cwd=REPO_ROOT / "backend",
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as exc:  # pragma: no cover
        warn(f"Could not run the backend to inspect settings: {exc}")
        return

    if proc.returncode != 0:
        warn("Could not import the backend settings (dependencies not installed?). "
             f"Last line: {proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else 'n/a'}")
        return

    try:
        report = json.loads(proc.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):  # pragma: no cover
        warn("The backend settings probe returned unreadable output.")
        return

    print(f"  env files loaded           : {report.get('env_files') or 'NONE'}")
    print(f"  storage dir                : {report.get('storage_dir')}")
    print(f"  serverless (/tmp storage)  : {report.get('is_serverless')}")
    print(f"  auth required              : {report.get('auth_required')}")
    print(f"  VIDEO_PROVIDER setting     : {report.get('video_provider_setting')}")
    print(f"  provider actually resolved : {report.get('video_provider')}")

    if not report.get("env_files"):
        fail("The backend loaded NO environment file, so it has no API keys. This is the "
             "usual \"works on my machine\" cause. Run `python scripts/setup_env.py`.")
    if not report.get("configured", {}).get("ai_vision"):
        warn("The backend sees no Gemini key: AI scene understanding will be unavailable.")


def check_live_backend(url: str) -> None:
    section(f"5. Live backend at {url}")
    endpoint = url.rstrip("/") + "/api/health"
    try:
        with urllib.request.urlopen(endpoint, timeout=15) as response:
            payload = json.loads(response.read().decode())
    except (urllib.error.URLError, OSError, ValueError) as exc:
        fail(f"Could not read {endpoint}: {exc}. Is the backend running and is "
             "NEXT_PUBLIC_API_URL pointing at it?")
        return

    data = payload.get("data") or {}
    ok(f"Backend reachable: version={data.get('version')} provider={data.get('video_provider')}")
    print(f"  auth_required  : {data.get('auth_required')}")
    print(f"  env files      : {data.get('env_files')}")
    print(f"  configured     : {data.get('configured')}")

    if data.get("is_serverless"):
        warn("The backend is running serverless: storage is ephemeral (/tmp) and long "
             "renders may exceed the function timeout. See docs/deployment-vercel.md.")
    if data.get("setup_hint"):
        fail(data["setup_hint"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", help="Also probe a running backend, e.g. https://api.example.com")
    parser.add_argument(
        "--skip-backend",
        action="store_true",
        help="Skip importing the backend settings (no virtualenv required).",
    )
    args = parser.parse_args()

    print("CinéEstate — configuration check")
    print(f"Repository: {REPO_ROOT}")

    backend_values, frontend_values = check_files()
    check_api_key(backend_values, frontend_values)
    check_providers(backend_values)
    if not args.skip_backend:
        check_backend_settings()
    if args.url:
        check_live_backend(args.url)

    print("\n" + "=" * 66)
    if PROBLEMS:
        print(f"\033[31m{len(PROBLEMS)} problem(s) — the app will misbehave:\033[0m")
        for item in PROBLEMS:
            print(f"  * {item}")
    if NOTES:
        print(f"\033[33m{len(NOTES)} note(s):\033[0m")
        for item in NOTES:
            print(f"  * {item}")
    if not PROBLEMS:
        print("\033[32mNo blocking problems found.\033[0m")

    return 1 if PROBLEMS else 0


if __name__ == "__main__":
    sys.exit(main())
