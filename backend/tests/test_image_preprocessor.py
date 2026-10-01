from pathlib import Path
import pytest
from tests.helpers import create_test_image_bytes
from app.core.errors import (
    ImageCorruptedError,
    ImageTooLargeError,
    ImageTooSmallError,
    InvalidImageFormatError,
)
from app.services.image_preprocessor import ImagePreprocessor


def test_preprocessor_validate_jpeg():
    preprocessor = ImagePreprocessor()
    img_bytes = create_test_image_bytes(width=1600, height=1200, img_format="JPEG")
    meta = preprocessor.validate_and_extract_metadata(img_bytes, "photo.jpg")

    assert meta["width"] == 1600
    assert meta["height"] == 1200
    assert meta["format"] == "JPEG"
    assert meta["aspect_ratio"] == 1.3333
    assert len(meta["sha256"]) == 64


def test_preprocessor_rejects_undersized():
    preprocessor = ImagePreprocessor()
    img_bytes = create_test_image_bytes(width=400, height=300)
    with pytest.raises(ImageTooSmallError):
        preprocessor.validate_and_extract_metadata(img_bytes, "small.jpg")


def test_preprocessor_rejects_corrupted():
    preprocessor = ImagePreprocessor()
    corrupted_bytes = b"NOT AN IMAGE FILE HEADER"
    with pytest.raises(ImageCorruptedError):
        preprocessor.validate_and_extract_metadata(corrupted_bytes, "bad.jpg")


def test_preprocessor_generate_thumbnail(tmp_path):
    preprocessor = ImagePreprocessor()
    img_bytes = create_test_image_bytes(width=1920, height=1080)
    thumb_path = tmp_path / "thumb.jpg"
    result_path = preprocessor.generate_thumbnail(img_bytes, thumb_path, max_size=(300, 300))

    assert result_path.exists()
    assert result_path.stat().st_size > 0
