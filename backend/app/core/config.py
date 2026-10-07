from pathlib import Path
from typing import List, Optional, Union
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


class Settings(BaseSettings):
    PROJECT_NAME: str = "Image-to-Video Walkthrough Generation"
    VERSION: str = "0.1.0"
    API_PREFIX: str = "/api"
    
    # Storage configuration
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    STORAGE_DIR: Path = Field(default=None)

    # Optional shared secret for this API. When set, every /api request must present it
    # in the `X-API-Key` header (or a `key` query parameter, for clients that cannot set
    # headers). Unset means no gate, which is fine for localhost-only development but
    # NOT for anything reachable from the internet — the API can spend provider quota.
    API_ACCESS_KEY: Optional[str] = None
    
    # Image constraints
    MAX_IMAGE_SIZE_BYTES: int = 20 * 1024 * 1024  # 20 MB
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
    AI_MODEL: str = "gemini-2.5-flash"  # default vision model
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

    @field_validator("STORAGE_DIR", mode="before")
    @classmethod
    def set_storage_dir(cls, v, info):
        if v is None:
            # Default to backend/storage
            return Path(__file__).resolve().parent.parent.parent / "storage"
        return Path(v)

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
