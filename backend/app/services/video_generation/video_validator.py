import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import cv2
from app.core.logging import logger
from app.schemas.generation import QualityAssessment


class VideoValidator:
    """
    Validates generated MP4 video files, extracts actual physical container metadata,
    and performs basic automated visual quality checks.
    """

    @staticmethod
    def validate_and_extract_metadata(
        video_path: Path,
        expected_min_duration: float = 1.0,
    ) -> Tuple[bool, Dict[str, Any], QualityAssessment, Optional[str]]:
        """
        Validates the video file and extracts duration, width, height, fps, and file size.
        Returns:
            (is_valid, metadata_dict, quality_assessment, error_message)
        """
        if not video_path.exists():
            return False, {}, QualityAssessment.FAILED, f"Video file not found at: {video_path}"

        file_size = os.path.getsize(video_path)
        if file_size < 1024:
            return False, {}, QualityAssessment.FAILED, f"Video file is truncated or empty ({file_size} bytes)."

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            return False, {}, QualityAssessment.FAILED, "Cannot open video container. Codec or format unreadable."

        try:
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = float(cap.get(cv2.CAP_PROP_FPS)) or 24.0
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            if width <= 0 or height <= 0:
                return False, {}, QualityAssessment.FAILED, f"Invalid video dimensions: {width}x{height}"

            # Calculate duration
            if frame_count > 0 and fps > 0:
                duration_seconds = round(frame_count / fps, 2)
            else:
                duration_seconds = 0.0

            # Read test frames to ensure stream can actually decode
            ret, first_frame = cap.read()
            if not ret or first_frame is None:
                return False, {}, QualityAssessment.FAILED, "Video stream exists but cannot decode initial frame."

            # Quality Assessment Heuristics
            quality = QualityAssessment.ACCEPTABLE
            # Check for totally black / blank frames
            mean_val = float(first_frame.mean())
            if mean_val < 2.0:
                quality = QualityAssessment.NEEDS_REVIEW
                logger.warning(f"Video {video_path.name} initial frame appears pitch black (mean={mean_val:.2f})")

            # Check if duration is too short
            if duration_seconds < expected_min_duration:
                quality = QualityAssessment.NEEDS_REVIEW
                logger.warning(
                    f"Video {video_path.name} duration ({duration_seconds}s) is shorter than expected minimum ({expected_min_duration}s)"
                )

            metadata = {
                "width": width,
                "height": height,
                "fps": fps,
                "frame_count": frame_count,
                "duration_seconds": max(duration_seconds, 1.0),
                "file_size_bytes": file_size,
                "format": "mp4",
            }

            return True, metadata, quality, None

        except Exception as e:
            logger.error(f"Error during video validation for {video_path}: {e}")
            return False, {}, QualityAssessment.FAILED, f"Video validation exception: {str(e)}"
        finally:
            cap.release()
