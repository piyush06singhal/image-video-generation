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
from app.services.project_service import project_service
from app.services.scene_service import scene_service
from app.services.walkthrough_planner import walkthrough_planner


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
    
    test_storage = StorageService(base_storage_dir=temp_storage)
    project_service.storage = test_storage
    scene_service.storage = test_storage
    walkthrough_planner.storage = test_storage
    
    yield test_storage
    
    # Cleanup and restore
    project_service.storage = original_project_storage
    scene_service.storage = original_scene_storage
    walkthrough_planner.storage = original_planner_storage



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
