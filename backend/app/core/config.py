import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


# ---------------------------------------------------------------------------
# Environment files
# ---------------------------------------------------------------------------
# These are ABSOLUTE paths on purpose.
#
# pydantic-settings resolves a relative ``env_file`` against the *process working
# directory*. With the original ``env_file=".env"`` the backend therefore only saw
# its keys when uvicorn happened to be launched from inside ``backend/``. Launching
# it from the repository root (or from an IDE run configuration, or from a
# different shell) silently produced a backend with no API keys at all — the
# single most common reason the same commit "works on my machine" but not on a
# fresh clone.
#
# ``backend/.env`` is listed last, and later files win, so a project-root ``.env``
# supplies shared defaults that the backend file can override.
BACKEND_DIR: Path = Path(__file__).resolve().parent.parent.parent
PROJECT_ROOT: Path = BACKEND_DIR.parent

ENV_FILES: tuple = (PROJECT_ROOT / ".env", BACKEND_DIR / ".env")


def _running_serverless() -> bool:
    """True when the process is a Vercel / Lambda-style ephemeral function."""
    return bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))


class Settings(BaseSettings):
    PROJECT_NAME: str = "Image-to-Video Walkthrough Generation"
    VERSION: str = "0.1.0"
    API_PREFIX: str = "/api"
    
    # Storage configuration
    BASE_DIR: Path = BACKEND_DIR
    STORAGE_DIR: Path = Field(default=None)
    REMOTE_STORAGE_ENABLED: bool = False
    SUPABASE_URL: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    SUPABASE_STORAGE_BUCKET: str = "walkthrough-assets"
    ASSEMBLY_MAX_RESOLUTION: Optional[str] = None

    # True when running as an ephemeral function (Vercel), where the only writable
    # path is /tmp and nothing survives between requests. Surfaced by /api/health
    # so an operator can tell a permanent deployment from a demo one at a glance.
    IS_SERVERLESS: bool = Field(default_factory=_running_serverless)

    # Optional shared secret for this API. When set, every /api request must present it
    # in the `X-API-Key` header (or a `key` query parameter, for clients that cannot set
    # headers). Unset means no gate, which is fine for localhost-only development but
    # NOT for anything reachable from the internet — the API can spend provider quota.
    API_ACCESS_KEY: Optional[str] = None
    
    # Image constraints
    MAX_IMAGE_SIZE_BYTES: int = 20 * 1024 * 1024  # 20 MB
    # A small file can still declare an enormous canvas (a decompression bomb):
    # decoding it allocates width*height*4 bytes, so the byte limit alone does not
    # protect the server. Canvases above this pixel count are rejected before decode.
    MAX_IMAGE_PIXELS: int = 40_000_000  # ~40 MP (an 8000x5000 photo)
    MAX_IMAGES_PER_PROJECT: int = 20
    MAX_ACTIVE_PROJECTS: int = 10
    MIN_IMAGE_WIDTH: int = 512
    MIN_IMAGE_HEIGHT: int = 512
    MAX_ANALYSIS_IMAGE_DIMENSION: int = 1536
    ALLOWED_IMAGE_FORMATS: List[str] = ["JPEG", "PNG", "WEBP"]
    ALLOWED_MIME_TYPES: List[str] = ["image/jpeg", "image/png", "image/webp"]
    
    # AI Provider Configuration
    AI_PROVIDER: str = "gemini"  # "gemini"
    GEMINI_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    AI_MODEL: str = "gemini-3.8-flash"  # default vision model
    AI_REQUEST_TIMEOUT_SECONDS: float = 30.0

    # Image-to-Video Generation Configuration (Phase 4)
    # Selects the active image-to-video backend:
    #   "auto"       -> try the remote provider, fall back to local Ken Burns on quota/block
    #   "gemini_veo" -> Google Veo only
    #   "kenburns"   -> fully local cinematic camera motion (no API, no quota)
    VIDEO_PROVIDER: str = "auto"
    VIDEO_API_KEY: Optional[str] = None
    VIDEO_MODEL: str = "veo-3.1-generate-preview"
    # When True, remote rate-limit/quota/content failures automatically degrade to the
    # local cinematic provider so a walkthrough is always produced during a demo.
    VIDEO_FALLBACK_TO_LOCAL: bool = True
    # Local cinematic (Ken Burns) provider output specification.
    KENBURNS_WIDTH: int = 1920
    KENBURNS_HEIGHT: int = 1080
    KENBURNS_FPS: float = 24.0

    # 2.5D depth parallax for the local renderer. A monocular depth model (Depth
    # Anything V2 Small, ONNX) estimates how far away each pixel is, and the
    # camera then moves near pixels further than far ones — the parallax that makes
    # a shot read as three-dimensional instead of as a panning photograph.
    # Everything degrades safely: with no model file the renderer falls back to a
    # flat affine move rather than failing.
    DEPTH_MODEL_PATH: Optional[str] = None  # defaults to backend/models/depth_anything_v2_small.onnx
    DEPTH_PARALLAX_ENABLED: bool = True
    # How far the nearest plane slides relative to the farthest, as a fraction of
    # the pan distance. Higher is punchier and more obviously 3D; too high and the
    # disocclusion between planes starts to smear.
    DEPTH_PARALLAX_STRENGTH: float = 0.85
    # Depth-proportional magnification during a push-in, so a foreground object
    # grows faster than the wall behind it.
    DEPTH_ZOOM_PARALLAX: float = 0.55
    # Trailing-shutter accumulation: real cameras blur fast motion, which is one of
    # the strongest "this is footage, not a still" cues. 0 disables the effect.
    MOTION_BLUR_SHUTTER: float = 0.62
    # Depth-of-field: keep the far plane slightly soft while the near plane stays
    # crisp. Off by default because wide-angle interior photography is deep-focus.
    RACK_FOCUS_STRENGTH: float = 0.0

    # Cloud renderer (JSON2Video): composites the real photos with pan/zoom,
    # transitions and title cards. No diffusion model, so the property can never be
    # hallucinated. Generous free tier, and it offloads rendering from this server.
    JSON2VIDEO_API_KEY: Optional[str] = None
    JSON2VIDEO_API_URL: str = "https://api.json2video.com/v2/movies"
    JSON2VIDEO_RESOLUTION: str = "full-hd"
    JSON2VIDEO_POLL_INTERVAL_SECONDS: float = 5.0
    JSON2VIDEO_TIMEOUT_SECONDS: float = 300.0
    # The JSON2Video docs describe 5xx as "no movie was created": retry with exponential
    # backoff rather than degrading the clip to the local renderer.
    JSON2VIDEO_MAX_RETRIES: int = 3
    JSON2VIDEO_BACKOFF_SECONDS: float = 2.0
    # JSON2Video's renderers *download* each source photo over HTTP, so this backend
    # must be reachable from the public internet. Set this to the public origin
    # (a tunnel or deployed host), e.g. "https://my-tunnel.ngrok.app". When unset the
    # JSON2Video provider reports itself as unconfigured and the pipeline degrades
    # to the local provider instead of failing.
    PUBLIC_BASE_URL: Optional[str] = None

    # Magic Hour image-to-video (generative alternative / fallback). Magic Hour's
    # single-shot REST API runs a diffusion video model over one still, so the
    # camera genuinely moves — at the cost of synthesising new pixels, which can
    # drift from the listing. Unlike JSON2Video it needs no public URL: the photo
    # is uploaded through /v1/files/upload-urls, so it works from localhost with
    # no tunnel. A missing key, exhausted credits, auth failure or timeout all
    # degrade to the local renderer instead of failing the walkthrough.
    MAGIC_HOUR_API_KEY: Optional[str] = None
    MAGIC_HOUR_API_URL: str = "https://api.magichour.ai/v1"
    # Pinned model, e.g. "kling-3.0", "ltx-2.5", "veo3.1". Unset means "let Magic
    # Hour use the model this account is entitled to" (paid -> kling-3.0, free ->
    # ltx-2.5), which is the safest default for an unknown plan.
    MAGIC_HOUR_MODEL: Optional[str] = None
    # Pinned output frame size: 360p | 480p | 720p | 1080p | 4k. Unset means the
    # plan's default. A rejection that cites the plan/tier is retried once without
    # this value, so pinning 1080p cannot dead-end a free-tier key.
    MAGIC_HOUR_RESOLUTION: Optional[str] = "720p"
    # Generative model audio is off by default: the assembler owns the soundtrack
    # (music_engine score + cut accents), so native audio would double up.
    MAGIC_HOUR_AUDIO: bool = False
    MAGIC_HOUR_POLL_INTERVAL_SECONDS: float = 5.0
    # Generative clips take minutes to render, so the poll budget is generous.
    MAGIC_HOUR_TIMEOUT_SECONDS: float = 900.0
    MAGIC_HOUR_MAX_RETRIES: int = 3
    MAGIC_HOUR_BACKOFF_SECONDS: float = 2.0

    # Free-tier Veo projects are burst-sensitive. Keep one remote generation
    # in flight by default; deployments with paid quota can raise this safely.
    MAX_CONCURRENT_GENERATIONS: int = 1
    VIDEO_DURATION_SECONDS: int = 4
    VIDEO_FPS: int = 24
    VIDEO_ASPECT_RATIO: str = "16:9"
    VIDEO_RESOLUTION: str = "720p"
    VIDEO_POLL_INTERVAL_SECONDS: float = 10.0
    VIDEO_POLL_TIMEOUT_SECONDS: float = 300.0
    VIDEO_SUBMISSION_INTERVAL_SECONDS: float = 10.0
    VIDEO_RATE_LIMIT_RETRY_ATTEMPTS: int = 3
    VIDEO_RATE_LIMIT_BACKOFF_SECONDS: float = 15.0
    MAX_GENERATION_RETRIES: int = 3
    MAX_SCENES_PER_GENERATION_REQUEST: int = 5
    
    # CORS
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]
    # Optional regex for origins whose hostname is not stable.
    #
    # Vercel assigns a NEW url to every preview deployment
    # (``<project>-git-<branch>-<user>.vercel.app``), so a static allow-list breaks
    # on every branch build and the failure looks like a dead backend. With the
    # frontend on Vercel and the backend elsewhere this is the normal case, so the
    # regex is the practical way to keep previews working.
    #
    # This is not a security boundary: the browser never attaches the shared key
    # on its own, and ``NEXT_PUBLIC_API_KEY`` is inlined into the public frontend
    # bundle anyway. Restrict this if you add real authentication.
    # Example: ``^https://[a-z0-9-]+(\.git-[a-z0-9-]+)?\.vercel\.app$``
    CORS_ORIGIN_REGEX: Optional[str] = None

    @field_validator("STORAGE_DIR", mode="before")
    @classmethod
    def set_storage_dir(cls, v, info):
        """Resolves STORAGE_DIR against the backend package, never the CWD.

        A relative ``STORAGE_DIR=storage`` used to be resolved against the working
        directory, so starting the backend from the repository root wrote projects
        to ``<repo>/storage`` while a start from ``backend/`` wrote them to
        ``backend/storage``. Two directories, one app, and "my project vanished".
        """
        if v is None:
            path = BACKEND_DIR / "storage"
        else:
            path = Path(v)
            if not path.is_absolute():
                path = BACKEND_DIR / path

        # A serverless filesystem is read-only apart from /tmp, and /tmp is
        # discarded between invocations. Redirect there so the app can still boot
        # and serve a demo instead of crashing on mkdir.
        if _running_serverless() and not str(path).startswith("/tmp"):
            return Path("/tmp") / "storage"
        return path

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    model_config = {
        # Absolute paths: see the ENV_FILES comment at the top of this module.
        "env_file": ENV_FILES,
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------
    @property
    def loaded_env_files(self) -> List[str]:
        """Which environment files exist, as repo-relative names.

        Names only — a path is a useful diagnostic, a value is a secret.
        """
        names: List[str] = []
        for path in ENV_FILES:
            if path.is_file():
                try:
                    names.append(str(path.relative_to(PROJECT_ROOT)))
                except ValueError:  # pragma: no cover - outside the repository
                    names.append(path.name)
        return names

    def configuration_report(self) -> Dict[str, Any]:
        """Names-only summary of what this process actually loaded.

        Returns booleans rather than the secret values themselves, so it is safe
        to expose from the unauthenticated health endpoint. When a remote provider
        looks "configured" in the UI but every clip comes back from the local
        renderer, this report is what says why.
        """
        return {
            "env_files": self.loaded_env_files,
            "storage_dir": str(self.STORAGE_DIR),
            "is_serverless": self.IS_SERVERLESS,
            "auth_required": bool(self.API_ACCESS_KEY),
            "durable_storage": bool(
                self.REMOTE_STORAGE_ENABLED
                and self.SUPABASE_URL
                and self.SUPABASE_SERVICE_ROLE_KEY
            ),
            "durable_storage_requested": self.REMOTE_STORAGE_ENABLED,
            "configured": {
                "ai_vision": bool(self.GEMINI_API_KEY or self.GOOGLE_API_KEY),
                "any_remote_video_provider": bool(self.MAGIC_HOUR_API_KEY)
                or bool(self.JSON2VIDEO_API_KEY and self.PUBLIC_BASE_URL)
                or bool(self.VIDEO_API_KEY or self.GEMINI_API_KEY or self.GOOGLE_API_KEY),
                "magic_hour": bool(self.MAGIC_HOUR_API_KEY),
                "json2video": bool(self.JSON2VIDEO_API_KEY),
                "json2video_source_url": bool(self.PUBLIC_BASE_URL),
            },
            "video_provider_setting": self.VIDEO_PROVIDER,
            "fallback_to_local": self.VIDEO_FALLBACK_TO_LOCAL,
        }


settings = Settings()
