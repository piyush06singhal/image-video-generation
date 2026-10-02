import io
from pathlib import Path
from typing import Any, Dict, Tuple
from PIL import Image, ImageFilter, ImageOps, ImageStat

from app.core.config import settings
from app.core.errors import (
    ImageCorruptedError,
    ImageTooLargeError,
    ImageTooSmallError,
    InvalidImageFormatError,
)
from app.core.logging import logger
from app.schemas.scene import ImageQualityResult, QualityStatus
from app.utils.file_utils import calculate_sha256


class ImagePreprocessor:
    """
    Service responsible for image validation, metadata extraction, derived thumbnail generation,
    analysis-ready normalized image preparation, and quantitative quality estimation.
    Preserves original uploaded files untouched for downstream AI processing.
    """

    def __init__(self):
        self.max_size_bytes = settings.MAX_IMAGE_SIZE_BYTES
        self.min_width = settings.MIN_IMAGE_WIDTH
        self.min_height = settings.MIN_IMAGE_HEIGHT
        self.allowed_formats = set(settings.ALLOWED_IMAGE_FORMATS)
        self.max_analysis_dim = settings.MAX_ANALYSIS_IMAGE_DIMENSION

    def validate_and_extract_metadata(
        self, file_bytes: bytes, original_filename: str
    ) -> Dict[str, Any]:
        """
        Validates the image file bytes and extracts structural metadata.
        Raises specific AppException subclasses if validation fails.
        """
        # 1. Check file size
        file_size = len(file_bytes)
        if file_size == 0:
            raise ImageCorruptedError("Uploaded image file is empty (0 bytes).")

        if file_size > self.max_size_bytes:
            raise ImageTooLargeError(file_size, self.max_size_bytes)

        # 2. Verify image integrity and readability with Pillow
        try:
            verify_buffer = io.BytesIO(file_bytes)
            test_img = Image.open(verify_buffer)
            format_name = (test_img.format or "").upper()
            test_img.verify()
        except Exception as e:
            logger.warning(f"Image integrity verification failed for {original_filename}: {e}")
            raise ImageCorruptedError(f"Corrupted or invalid image file: {original_filename}")

        if format_name == "JPG":
            format_name = "JPEG"

        if format_name not in self.allowed_formats:
            raise InvalidImageFormatError(format_name, list(self.allowed_formats))

        # 3. Read actual image dimensions (accounting for EXIF orientation)
        try:
            read_buffer = io.BytesIO(file_bytes)
            with Image.open(read_buffer) as img:
                oriented_img = ImageOps.exif_transpose(img)
                if oriented_img is not None:
                    width, height = oriented_img.size
                else:
                    width, height = img.size
        except Exception as e:
            logger.warning(f"Failed to read image dimensions for {original_filename}: {e}")
            raise ImageCorruptedError(f"Failed to decode image dimensions: {original_filename}")

        # 4. Dimension checks
        if width < self.min_width or height < self.min_height:
            raise ImageTooSmallError(width, height, self.min_width, self.min_height)

        aspect_ratio = round(float(width) / float(height), 4)
        sha256_hash = calculate_sha256(file_bytes)

        # Phase 6: Automated equirectangular panorama detection (2:1 aspect ratio)
        is_equirectangular = 1.92 <= aspect_ratio <= 2.08 and width >= 1024
        is_panoramic_detected = is_equirectangular
        panoramic_type = "equirectangular" if is_equirectangular else ("wide" if aspect_ratio >= 1.6 else "perspective")

        return {
            "width": width,
            "height": height,
            "format": format_name,
            "file_size": file_size,
            "aspect_ratio": aspect_ratio,
            "sha256": sha256_hash,
            "is_panoramic": is_equirectangular,
            "is_panoramic_detected": is_panoramic_detected,
            "panoramic_type": panoramic_type,
        }

    def generate_thumbnail(
        self,
        file_bytes: bytes,
        output_path: Path,
        max_size: Tuple[int, int] = (480, 480),
    ) -> Path:
        """
        Generates a clean web-optimized thumbnail inside the processed/ directory.
        Original image is untouched.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        buffer = io.BytesIO(file_bytes)
        with Image.open(buffer) as img:
            oriented_img = ImageOps.exif_transpose(img)
            target = oriented_img if oriented_img is not None else img

            if target.mode in ("RGBA", "LA", "P"):
                rgb_img = Image.new("RGB", target.size, (255, 255, 255))
                if target.mode == "RGBA":
                    rgb_img.paste(target, mask=target.split()[3])
                else:
                    rgb_img.paste(target.convert("RGB"))
                target = rgb_img
            elif target.mode != "RGB":
                target = target.convert("RGB")

            target.thumbnail(max_size, Image.Resampling.LANCZOS)
            target.save(output_path, format="JPEG", quality=85, optimize=True)

        return output_path

    def prepare_analysis_image(
        self,
        file_bytes: bytes,
        output_path: Path,
    ) -> Tuple[Path, ImageQualityResult]:
        """
        Phase 2 Preprocessing:
        - Normalizes orientation via EXIF
        - Converts color spaces to standard RGB (preventing CMYK / alpha issues)
        - Downscales proportionally if exceeding max_analysis_dim (preserving full aspect ratio, no cropping)
        - Saves to processed/analysis_{image_id}.jpg
        - Computes real mathematical quality metrics (brightness, contrast, sharpness, status)
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        buffer = io.BytesIO(file_bytes)
        with Image.open(buffer) as img:
            # 1. Normalize orientation
            oriented_img = ImageOps.exif_transpose(img)
            target = oriented_img if oriented_img is not None else img

            # 2. Convert color mode to standard RGB
            if target.mode in ("RGBA", "LA", "P"):
                rgb_img = Image.new("RGB", target.size, (255, 255, 255))
                if target.mode == "RGBA":
                    rgb_img.paste(target, mask=target.split()[3])
                else:
                    rgb_img.paste(target.convert("RGB"))
                target = rgb_img
            elif target.mode != "RGB":
                target = target.convert("RGB")

            orig_w, orig_h = target.size

            # 3. Compute image quality metrics on oriented RGB image
            quality_result = self.calculate_quality_metrics(target, len(file_bytes))

            # 4. Proportional scaling for vision model efficiency if larger than max_analysis_dim
            max_dim = max(orig_w, orig_h)
            if max_dim > self.max_analysis_dim:
                scale = self.max_analysis_dim / float(max_dim)
                new_w = int(orig_w * scale)
                new_h = int(orig_h * scale)
                analysis_img = target.resize((new_w, new_h), Image.Resampling.LANCZOS)
            else:
                analysis_img = target

            # 5. Save analysis-ready file preserving high fidelity
            analysis_img.save(output_path, format="JPEG", quality=92, optimize=True)

        return output_path, quality_result

    def calculate_quality_metrics(
        self, image: Image.Image, file_size: int
    ) -> ImageQualityResult:
        """
        Calculates mathematical image quality indicators:
        - Brightness: mean grayscale luminance (0.0 to 1.0)
        - Contrast: standard deviation of grayscale luminance normalized (0.0 to 1.0)
        - Sharpness: high-frequency edge variance via edge detection filter (0.0 to 1.0)
        - Overall quality classification: good, acceptable, poor
        """
        width, height = image.size
        resolution_str = f"{width}x{height}"

        # Convert to grayscale for illumination & edge analysis
        gray = image.convert("L")
        stat = ImageStat.Stat(gray)

        # 1. Brightness: mean pixel value in [0, 255] normalized to [0.0, 1.0]
        mean_brightness = stat.mean[0] if stat.mean else 128.0
        brightness_score = round(min(1.0, max(0.0, mean_brightness / 255.0)), 3)

        # 2. Contrast: standard deviation in [0, 255] normalized
        stddev_contrast = stat.stddev[0] if stat.stddev else 40.0
        contrast_score = round(min(1.0, max(0.0, (stddev_contrast * 2.0) / 255.0)), 3)

        # 3. Sharpness / Blur estimation using edge variance
        edges = gray.filter(ImageFilter.FIND_EDGES)
        edge_stat = ImageStat.Stat(edges)
        edge_variance = edge_stat.stddev[0] if edge_stat.stddev else 10.0
        sharpness_score = round(min(1.0, max(0.0, edge_variance / 45.0)), 3)

        # 4. Determine input-quality status
        # Good: Good resolution, well balanced lighting, good contrast and sharpness
        # Acceptable: Valid dimensions, reasonable lighting
        # Poor: Severely underexposed/overexposed, extreme blur, or close to lower limit
        is_lighting_good = 0.22 <= brightness_score <= 0.82
        is_lighting_acceptable = 0.12 <= brightness_score <= 0.94
        is_sharpness_good = sharpness_score >= 0.22
        is_sharpness_acceptable = sharpness_score >= 0.10
        is_resolution_good = width >= 800 and height >= 600

        if is_lighting_good and is_sharpness_good and is_resolution_good and contrast_score >= 0.25:
            status = QualityStatus.GOOD
        elif is_lighting_acceptable and is_sharpness_acceptable:
            status = QualityStatus.ACCEPTABLE
        else:
            status = QualityStatus.POOR

        return ImageQualityResult(
            status=status,
            resolution=resolution_str,
            brightness_score=brightness_score,
            contrast_score=contrast_score,
            sharpness_score=sharpness_score,
            file_size=file_size,
        )


# Global instance
image_preprocessor = ImagePreprocessor()
