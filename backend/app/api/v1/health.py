from typing import Any, Dict

from fastapi import APIRouter

from app.core.config import settings
from app.schemas.common import ApiResponse
from app.services.video_generation.factory import resolve_video_provider_name

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=ApiResponse[Dict[str, Any]])
async def health_check():
    """
    Service health and capability report.

    This endpoint is deliberately exempt from the API-key guard: the studio probes
    it *before* it has any credentials, and it is the one place a misconfigured
    deployment can explain itself.

    It reports which providers are configured as booleans and file *names* only.
    No key, token or secret value is ever included — see
    ``Settings.configuration_report``. The studio uses ``auth_required`` to tell the
    operator that the backend wants an ``X-API-Key`` while this frontend build has
    none, which is otherwise indistinguishable from "the server is down".
    """
    data: Dict[str, Any] = {
        "status": "healthy",
        "service": "walkthrough-backend",
        "version": settings.VERSION,
        "video_provider": resolve_video_provider_name(),
    }
    data.update(settings.configuration_report())

    # A freshly cloned checkout has no .env at all. Say so explicitly instead of
    # reporting a clean bill of health that the first real request contradicts.
    # Deployments that configure through real environment variables (Render,
    # Docker, CI) deliberately have no .env file, so the file-based hint would be
    # misleading there — only emit it when nothing was configured through either
    # channel.
    configured_outside_files = bool(
        data["configured"]["ai_vision"]
        or data["configured"]["any_remote_video_provider"]
        or data["auth_required"]
    )
    if not data["env_files"] and not configured_outside_files:
        data["setup_hint"] = (
            "No environment file was found. Run `python scripts/setup_env.py` from "
            "the repository root, or copy backend/.env.example to backend/.env and "
            "fill in your keys."
        )

    return ApiResponse.success_response(data=data)
