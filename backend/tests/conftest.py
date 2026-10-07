import io
import shutil
import tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.core.config import settings
from app.main import app
from app.services.storage_service import StorageService, storage_service
from app.services.evaluation_service import evaluation_service
from app.services.project_service import project_service
from app.services.render_options_service import render_options_service
from app.services.scene_service import scene_service
from app.services.video_generation import video_generation_service
from app.services.video_assembler import video_assembler_service
from app.services.walkthrough_planner import walkthrough_planner


@pytest.fixture(autouse=True, scope="session")
def _neutralize_api_access_key():
    """Runs the suite with the API access-key guard disabled.

    ``API_ACCESS_KEY`` is a deployment guard read from ``backend/.env``. A developer
    who has set it locally would otherwise turn almost every API test into a 401.
    The guard has its own tests (``test_api_access_key.py``), which opt back in with
    monkeypatch, so nothing about it goes unverified.
    """
    original = settings.API_ACCESS_KEY
    settings.API_ACCESS_KEY = None
    yield
    settings.API_ACCESS_KEY = original


@pytest.fixture(autouse=True, scope="session")
def _disable_depth_parallax_by_default():
    """Keeps the suite fast and deterministic.

    Turning on 2.5D parallax loads a ~100MB ONNX model and runs a transformer over
    every source image, which adds seconds to each clip render. Tests that actually
    exercise the parallax path opt back in explicitly, injecting a synthetic depth
    map so they never depend on the model file being present.
    """
    original = settings.DEPTH_PARALLAX_ENABLED
    settings.DEPTH_PARALLAX_ENABLED = False
    yield
    settings.DEPTH_PARALLAX_ENABLED = original


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path):
    """
    Redirects storage to a temporary directory for each test to ensure test isolation.
    """
    temp_storage = tmp_path / "test_storage"
    temp_storage.mkdir(parents=True, exist_ok=True)
    
    # Override storage in services
    original_project_storage = project_service.storage
    original_scene_storage = scene_service.storage
    original_planner_storage = walkthrough_planner.storage
    original_video_storage = video_generation_service.storage
    original_assembler_storage = video_assembler_service.storage
    original_eval_storage = evaluation_service.storage
    original_render_options_storage = render_options_service.storage

    # NOTE: every service that reads or writes project files must be redirected
    # here, otherwise tests leak into (and read from) the developer's real
    # backend/storage directory.
    test_storage = StorageService(base_storage_dir=temp_storage)
    project_service.storage = test_storage
    scene_service.storage = test_storage
    walkthrough_planner.storage = test_storage
    video_generation_service.storage = test_storage
    video_assembler_service.storage = test_storage
    evaluation_service.storage = test_storage
    render_options_service.storage = test_storage

    yield test_storage

    # Cleanup and restore
    project_service.storage = original_project_storage
    scene_service.storage = original_scene_storage
    walkthrough_planner.storage = original_planner_storage
    video_generation_service.storage = original_video_storage
    video_assembler_service.storage = original_assembler_storage
    evaluation_service.storage = original_eval_storage
    render_options_service.storage = original_render_options_storage



@pytest.fixture
def client():
    """
    FastAPI test client.
    """
    with TestClient(app) as test_client:
        yield test_client


def create_test_image_bytes(
    width: int = 800,
    height: int = 600,
    img_format: str = "JPEG",
    color: tuple = (100, 150, 200),
) -> bytes:
    """
    Generates valid image bytes in-memory for testing.
    """
    buffer = io.BytesIO()
    mode = "RGB" if img_format.upper() in ["JPEG", "JPG"] else "RGBA"
    image = Image.new(mode, (width, height), color)
    image.save(buffer, format=img_format)
    return buffer.getvalue()
