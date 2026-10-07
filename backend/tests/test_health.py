"""Tests for the self-describing /api/health payload.

A deployment whose provider key is missing used to look identical to a working one
until every clip silently came back from the local renderer, and a key mismatch
surfaced as an opaque 401 that read like a dead server. Health now reports what the
process actually loaded so the studio can explain both.
"""

from app.core.config import settings


def test_health_check(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["success"] is True
    assert json_data["data"]["status"] == "healthy"
    assert json_data["data"]["service"] == "walkthrough-backend"
    assert json_data["error"] is None


def test_health_reports_provider_and_auth_state(client):
    data = client.get("/api/health").json()["data"]

    assert data["video_provider"] in {
        "kenburns", "magic_hour", "json2video", "gemini_veo",
    }
    assert isinstance(data["auth_required"], bool)
    assert isinstance(data["env_files"], list)
    assert "configured" in data
    assert "video_provider_setting" in data
    assert "fallback_to_local" in data


def test_health_auth_flag_follows_the_guard(client, monkeypatch):
    monkeypatch.setattr(settings, "API_ACCESS_KEY", "some-secret")
    assert client.get("/api/health").json()["data"]["auth_required"] is True

    monkeypatch.setattr(settings, "API_ACCESS_KEY", None)
    assert client.get("/api/health").json()["data"]["auth_required"] is False


def test_health_never_leaks_secret_values(client, monkeypatch):
    """Health is unauthenticated, so it must expose booleans, never key material."""
    secret = "sk-super-secret-value-9876543210"
    monkeypatch.setattr(settings, "API_ACCESS_KEY", secret)
    monkeypatch.setattr(settings, "MAGIC_HOUR_API_KEY", secret)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", secret)

    body = client.get("/api/health").content.decode()
    assert secret not in body


def test_health_hints_when_no_env_file_loaded(client, monkeypatch):
    monkeypatch.setattr(
        type(settings), "loaded_env_files", property(lambda self: [])
    )
    data = client.get("/api/health").json()["data"]
    assert "setup_hint" in data
    assert "scripts/setup_env.py" in data["setup_hint"]
