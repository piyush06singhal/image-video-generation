"""Tests for the optional API_ACCESS_KEY guard.

The API had no inbound authentication at all, so anyone who could reach it (for example
through the public tunnel a cloud video renderer needs) could list, mutate and delete
every project and spend the configured provider quota.
"""

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

KEY = "test-access-key-0123456789"


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def guarded(monkeypatch):
    monkeypatch.setattr(settings, "API_ACCESS_KEY", KEY)


def test_unset_key_leaves_api_open(client, monkeypatch):
    """Local development must not suddenly require credentials."""
    monkeypatch.setattr(settings, "API_ACCESS_KEY", None)
    assert client.get("/api/projects").status_code == 200


def test_missing_key_is_rejected(client, guarded):
    resp = client.get("/api/projects")
    assert resp.status_code == 401
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "UNAUTHORIZED"


def test_wrong_key_is_rejected(client, guarded):
    resp = client.get("/api/projects", headers={"X-API-Key": "not-the-key"})
    assert resp.status_code == 401


def test_correct_header_key_is_accepted(client, guarded):
    resp = client.get("/api/projects", headers={"X-API-Key": KEY})
    assert resp.status_code == 200


def test_query_parameter_key_is_accepted(client, guarded):
    """Fallback for clients that cannot set headers."""
    resp = client.get("/api/projects", params={"key": KEY})
    assert resp.status_code == 200


def test_mutating_request_is_protected(client, guarded):
    resp = client.post("/api/projects", json={"name": "should not be created"})
    assert resp.status_code == 401


def test_health_stays_public(client, guarded):
    """The studio probes health before it has credentials."""
    assert client.get("/api/health").status_code == 200


def test_media_file_routes_stay_open(client, guarded):
    """<img>/<video> cannot send headers, so /file routes must remain reachable."""
    resp = client.get("/api/projects/does-not-exist/final-video/file")
    # Not 401 — the guard lets it through and the handler reports the missing project.
    assert resp.status_code != 401


@pytest.mark.parametrize(
    "path",
    [
        "/api/projects/p1/final-video/download",
        "/api/projects/p1/clips/s1/download",
        "/api/projects/p1/images/i1/thumbnail",
        "/api/projects/p1/images/i1/analysis-file",
    ],
)
def test_browser_media_routes_stay_open(client, guarded, path):
    """The media exemption must cover every route the browser fetches bare.

    The original guard only exempted paths *ending* in ``/file``, so with a key
    configured the studio's download buttons, the immersive scene player and the
    image grid thumbnails all returned 401 while every JSON call kept working —
    exactly the "keys don't work on another machine" symptom.
    """
    resp = client.get(path)
    assert resp.status_code != 401, f"{path} should be exempt from the API-key guard"


def test_non_media_paths_are_still_guarded(client, guarded):
    """Broadening the exemption must not open the JSON API."""
    assert client.get("/api/projects").status_code == 401
    assert client.get("/api/projects/p1/plan").status_code == 401
    assert client.get("/api/projects/p1").status_code == 401
