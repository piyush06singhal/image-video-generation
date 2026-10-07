"""Tests for environment resolution and the provider-selection diagnostics.

Two real cross-machine bugs live here:

* ``env_file`` was relative, so the backend only saw its keys when uvicorn was
  launched from inside ``backend/`` — the classic "works on my machine".
* ``STORAGE_DIR`` was resolved against the working directory too, so the same
  command started from the repository root wrote projects somewhere else entirely.
"""

import re
from pathlib import Path

import pytest

from app.core import config as config_module
from app.core.config import BACKEND_DIR, ENV_FILES, PROJECT_ROOT, Settings, settings
from app.services.video_generation import factory


def test_env_files_are_absolute():
    """A relative env_file silently depends on the caller's working directory."""
    for path in ENV_FILES:
        assert path.is_absolute(), f"{path} should be absolute"


def test_env_files_target_repo_root_and_backend():
    assert ENV_FILES[0] == PROJECT_ROOT / ".env"
    assert ENV_FILES[1] == BACKEND_DIR / ".env"


def test_relative_storage_dir_resolves_against_backend_package():
    # A relative STORAGE_DIR used to mean "relative to wherever you launched
    # uvicorn from", which silently forked the project store.
    assert Settings(STORAGE_DIR="storage").STORAGE_DIR == BACKEND_DIR / "storage"


def test_absolute_storage_dir_is_untouched():
    assert Settings(STORAGE_DIR="/tmp/custom").STORAGE_DIR == Path("/tmp/custom")


def test_serverless_storage_is_redirected_to_tmp(monkeypatch):
    """A function filesystem is read-only except /tmp, and /tmp does not persist."""
    monkeypatch.setenv("VERCEL", "1")
    redirected = Settings(STORAGE_DIR="storage").STORAGE_DIR
    assert str(redirected).startswith("/tmp")
    assert redirected.name == "storage"


def test_serverless_detection_ignores_local_runs(monkeypatch):
    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.delenv("AWS_LAMBDA_FUNCTION_NAME", raising=False)
    assert Settings(STORAGE_DIR="storage").STORAGE_DIR == BACKEND_DIR / "storage"


def test_loaded_env_files_are_repo_relative():
    names = settings.loaded_env_files
    for name in names:
        assert not name.startswith("/")
        assert name.endswith(".env")


def test_configuration_report_exposes_no_values():
    secret = "sk-probe-value-1234567890"
    settings.API_ACCESS_KEY = secret
    settings.MAGIC_HOUR_API_KEY = secret
    try:
        report = settings.configuration_report()
        rendered = str(report)
        assert secret not in rendered
        assert report["auth_required"] is True
        assert report["configured"]["magic_hour"] is True
        assert report["configured"]["any_remote_video_provider"] is True
        assert isinstance(report["env_files"], list)
    finally:
        settings.API_ACCESS_KEY = None
        settings.MAGIC_HOUR_API_KEY = None


# ---------------------------------------------------------------------------
# Provider selection diagnostics
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "setting,expected",
    [
        ("kenburns", "kenburns"),
        ("local", "kenburns"),
        ("magic_hour", "magic_hour"),
        ("magichour", "magic_hour"),
        ("json2video", "json2video"),
        ("gemini_veo", "gemini_veo"),
    ],
)
def test_resolve_provider_honours_explicit_settings(monkeypatch, setting, expected):
    monkeypatch.setattr(settings, "VIDEO_PROVIDER", setting)
    assert factory.resolve_video_provider_name() == expected


def test_auto_picks_magic_hour_before_veo(monkeypatch):
    monkeypatch.setattr(settings, "VIDEO_PROVIDER", "auto")
    monkeypatch.setattr(settings, "JSON2VIDEO_API_KEY", None)
    monkeypatch.setattr(settings, "PUBLIC_BASE_URL", None)
    monkeypatch.setattr(settings, "MAGIC_HOUR_API_KEY", "mh-key")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "gemini-key")
    assert factory.resolve_video_provider_name() == "magic_hour"


def test_auto_requires_public_base_url_for_json2video(monkeypatch):
    """A key without a reachable origin cannot serve source photos."""
    monkeypatch.setattr(settings, "VIDEO_PROVIDER", "auto")
    monkeypatch.setattr(settings, "JSON2VIDEO_API_KEY", "j2v-key")
    monkeypatch.setattr(settings, "PUBLIC_BASE_URL", None)
    monkeypatch.setattr(settings, "MAGIC_HOUR_API_KEY", "mh-key")
    assert factory.resolve_video_provider_name() == "magic_hour"


def test_auto_falls_through_to_local_when_nothing_is_configured(monkeypatch):
    monkeypatch.setattr(settings, "VIDEO_PROVIDER", "auto")
    monkeypatch.setattr(settings, "JSON2VIDEO_API_KEY", None)
    monkeypatch.setattr(settings, "PUBLIC_BASE_URL", None)
    monkeypatch.setattr(settings, "MAGIC_HOUR_API_KEY", None)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)
    monkeypatch.setattr(settings, "GOOGLE_API_KEY", None)
    monkeypatch.setattr(settings, "VIDEO_API_KEY", None)
    assert factory.resolve_video_provider_name() == "kenburns"


def test_unknown_setting_falls_back_to_auto(monkeypatch):
    monkeypatch.setattr(settings, "VIDEO_PROVIDER", "not-a-provider")
    monkeypatch.setattr(settings, "JSON2VIDEO_API_KEY", None)
    monkeypatch.setattr(settings, "PUBLIC_BASE_URL", None)
    monkeypatch.setattr(settings, "MAGIC_HOUR_API_KEY", None)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)
    monkeypatch.setattr(settings, "GOOGLE_API_KEY", None)
    monkeypatch.setattr(settings, "VIDEO_API_KEY", None)
    assert factory.resolve_video_provider_name() == "kenburns"


def test_auto_primary_name_and_instance_agree(monkeypatch):
    """The health report and the built provider must never disagree."""
    monkeypatch.setattr(settings, "VIDEO_PROVIDER", "auto")
    monkeypatch.setattr(settings, "JSON2VIDEO_API_KEY", None)
    monkeypatch.setattr(settings, "PUBLIC_BASE_URL", None)
    monkeypatch.setattr(settings, "MAGIC_HOUR_API_KEY", "mh-key")

    name = factory.resolve_video_provider_name()
    built = factory.build_video_provider()
    assert built.get_provider_name() == name


# ---------------------------------------------------------------------------
# CORS origins that are not stable
# ---------------------------------------------------------------------------
#
# Vercel assigns a new hostname to every preview deployment, so the frontend on
# Vercel and the backend elsewhere cannot rely on a static allow-list.

# The value recommended in render.yaml and docs/deployment-render.md.
VERCEL_ORIGIN_REGEX = r"^https://[a-z0-9-]+(\.git-[a-z0-9-]+)?\.vercel\.app$"


@pytest.mark.parametrize(
    "origin",
    [
        "https://cineestate.vercel.app",
        "https://cineestate-git-main-piyush.vercel.app",
        "https://image-video-generation-abc123.vercel.app",
    ],
)
def test_vercel_regex_matches_production_and_preview_origins(origin):
    assert re.match(VERCEL_ORIGIN_REGEX, origin), origin


@pytest.mark.parametrize(
    "origin",
    [
        "https://evil.com",
        "http://cineestate.vercel.app",          # http, not https
        "https://cineestate.vercel.app.evil.com",  # suffixed, not anchored
        "https://notvercel.app",
    ],
)
def test_vercel_regex_rejects_other_origins(origin):
    assert not re.match(VERCEL_ORIGIN_REGEX, origin), origin


def test_cors_regex_is_wired_into_the_app():
    """The setting must actually reach CORSMiddleware.

    It is read at middleware construction, so a typo would silently disable the
    regex and every Vercel preview build would be blocked by CORS — which the
    browser reports as a dead backend.
    """
    from starlette.middleware.cors import CORSMiddleware

    from app.main import app

    cors = [m for m in app.user_middleware if m.cls is CORSMiddleware]
    assert cors, "CORSMiddleware is not registered"
    kwargs = cors[-1].kwargs
    assert "allow_origin_regex" in kwargs
    # Unset must normalise to None, never to "" (which would match nothing) and
    # never to a wildcard.
    assert kwargs["allow_origin_regex"] == (settings.CORS_ORIGIN_REGEX or None)
    assert "*" not in (kwargs["allow_origins"] or [])


def test_cors_regex_admits_a_preview_origin_through_real_middleware():
    """End-to-end proof that the recommended regex works in CORSMiddleware."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from starlette.middleware.cors import CORSMiddleware

    preview_app = FastAPI()

    @preview_app.get("/api/health")
    async def _health():
        return {"ok": True}

    preview_app.add_middleware(
        CORSMiddleware,
        allow_origins=[],
        allow_origin_regex=VERCEL_ORIGIN_REGEX,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    client = TestClient(preview_app)
    allowed = "https://cineestate-git-main-piyush.vercel.app"
    resp = client.get("/api/health", headers={"Origin": allowed})
    assert resp.headers.get("access-control-allow-origin") == allowed

    blocked = client.get("/api/health", headers={"Origin": "https://evil.com"})
    assert "access-control-allow-origin" not in blocked.headers
