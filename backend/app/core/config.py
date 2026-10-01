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
    
    # Image constraints
    MAX_IMAGE_SIZE_BYTES: int = 20 * 1024 * 1024  # 20 MB
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
    VIDEO_PROVIDER: str = "gemini_veo"
    VIDEO_API_KEY: Optional[str] = None
    VIDEO_MODEL: str = "veo-3.1-generate-preview"
    MAX_CONCURRENT_GENERATIONS: int = 2
    VIDEO_DURATION_SECONDS: int = 4
    VIDEO_FPS: int = 24
    VIDEO_ASPECT_RATIO: str = "16:9"
    VIDEO_RESOLUTION: str = "720p"
    VIDEO_POLL_INTERVAL_SECONDS: float = 10.0
    VIDEO_POLL_TIMEOUT_SECONDS: float = 300.0
    MAX_GENERATION_RETRIES: int = 3
    
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
