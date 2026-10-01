import io
from PIL import Image


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
