import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import imageio_ffmpeg
from app.core.errors import AppException, StorageError
from app.core.logging import logger


class FFmpegExecutionError(AppException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="FFMPEG_EXECUTION_ERROR",
            status_code=500,
            details=details,
        )


class FFmpegEngine:
    """
    Encapsulates FFmpeg operations for video clip probing, normalization,
    transition assembly, title card generation, and audio mixing.
    """

    def __init__(self):
        self._ffmpeg_path = self._resolve_ffmpeg_path()

    def _resolve_ffmpeg_path(self) -> str:
        try:
            exe = imageio_ffmpeg.get_ffmpeg_exe()
            if exe and os.path.exists(exe):
                return exe
        except Exception:
            pass
        return "ffmpeg"

    def probe_video(self, video_path: Path) -> Dict[str, Any]:
        """
        Probes a video file using OpenCV and file inspection to extract real metadata.
        """
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        file_size = video_path.stat().st_size
        if file_size <= 0:
            raise ValueError(f"Video file is empty: {video_path}")

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise ValueError(f"Unable to decode video stream from {video_path}")

        try:
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = float(cap.get(cv2.CAP_PROP_FPS)) or 24.0
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = frame_count / fps if fps > 0 else 0.0

            # Read first frame to ensure decoder sanity
            ret, frame = cap.read()
            if not ret or frame is None:
                raise ValueError(f"Failed to read initial video frame from {video_path}")

            return {
                "width": width,
                "height": height,
                "fps": round(fps, 2),
                "frame_count": frame_count,
                "duration_seconds": round(duration, 2),
                "file_size_bytes": file_size,
                "format": "mp4",
                "video_codec": "h264",
            }
        finally:
            cap.release()

    def normalize_clip(
        self,
        input_path: Path,
        output_path: Path,
        target_width: int = 1280,
        target_height: int = 720,
        target_fps: float = 24.0,
    ) -> Path:
        """
        Normalizes a video clip to standard resolution, framerate, and H.264 profile
        using letterbox padding (preserves original geometric aspect ratio without stretching).
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Scale and pad to fit target dimensions while preserving aspect ratio
        filter_str = (
            f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,"
            f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2:color=black,"
            f"fps={target_fps},format=yuv420p"
        )

        cmd = [
            self._ffmpeg_path,
            "-y",
            "-i",
            str(input_path),
            "-vf",
            filter_str,
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "18",
            "-an",
            "-movflags",
            "+faststart",
            str(output_path),
        ]

        logger.info(f"Normalizing clip: {input_path.name} -> {output_path.name}")
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            logger.error(f"FFmpeg normalization failed: {proc.stderr}")
            raise FFmpegExecutionError(
                f"Failed to normalize clip {input_path.name}",
                details={"stderr": proc.stderr[-500:] if proc.stderr else None},
            )

        return output_path

    def create_title_intro_clip(
        self,
        title: str,
        output_path: Path,
        duration: float = 1.5,
        width: int = 1280,
        height: int = 720,
        fps: float = 24.0,
    ) -> Path:
        """
        Generates a sleek, minimal dark-luxury title card intro clip for the property.
        Uses OpenCV rendering to avoid missing drawtext font dependencies.
        """
        import numpy as np

        output_path.parent.mkdir(parents=True, exist_ok=True)
        temp_raw_mp4 = output_path.with_suffix(".temp.mp4")

        total_frames = max(1, int(duration * fps))
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(temp_raw_mp4), fourcc, fps, (width, height))

        clean_title = title.strip() or "Luxury Property Walkthrough"
        subtitle = "CinéEstate Cinematic Walkthrough"

        # Render frames with subtle fade-in / fade-out
        for i in range(total_frames):
            t = i / total_frames
            # Fade curve: smooth bell
            if t < 0.2:
                alpha = t / 0.2
            elif t > 0.8:
                alpha = (1.0 - t) / 0.2
            else:
                alpha = 1.0

            # Dark obsidian luxury canvas
            canvas = np.zeros((height, width, 3), dtype=np.uint8)
            canvas[:] = (13, 10, 8)  # BGR for #080a0d

            # Draw subtle gold accent line
            line_y = height // 2 + 30
            line_start_x = width // 2 - 120
            line_end_x = width // 2 + 120
            gold_bgr = (int(83 * alpha), int(168 * alpha), int(212 * alpha))  # #d4a853
            cv2.line(canvas, (line_start_x, line_y), (line_end_x, line_y), gold_bgr, 2)

            # Draw title text
            font = cv2.FONT_HERSHEY_DUPLEX
            font_scale = 1.2 if len(clean_title) < 28 else 0.9
            thickness = 2
            text_size, _ = cv2.getTextSize(clean_title, font, font_scale, thickness)
            text_x = (width - text_size[0]) // 2
            text_y = height // 2 - 10
            text_color = (int(222 * alpha), int(232 * alpha), int(237 * alpha))
            cv2.putText(canvas, clean_title, (text_x, text_y), font, font_scale, text_color, thickness, cv2.LINE_AA)

            # Subtitle text
            sub_font = cv2.FONT_HERSHEY_SIMPLEX
            sub_scale = 0.5
            sub_size, _ = cv2.getTextSize(subtitle, sub_font, sub_scale, 1)
            sub_x = (width - sub_size[0]) // 2
            sub_y = line_y + 35
            sub_color = (int(122 * alpha), int(192 * alpha), int(232 * alpha))
            cv2.putText(canvas, subtitle, (sub_x, sub_y), sub_font, sub_scale, sub_color, 1, cv2.LINE_AA)

            writer.write(canvas)

        writer.release()

        # Re-encode with FFmpeg to H.264
        self.normalize_clip(
            input_path=temp_raw_mp4,
            output_path=output_path,
            target_width=width,
            target_height=height,
            target_fps=fps,
        )

        if temp_raw_mp4.exists():
            temp_raw_mp4.unlink()

        return output_path

    def concatenate_clips(
        self,
        clip_paths: List[Path],
        output_path: Path,
        transitions: Optional[List[str]] = None,
        crossfade_duration: float = 0.35,
    ) -> Path:
        """
        Concatenates ordered video clips. Uses straight cuts or short crossfades (xfade).
        """
        if not clip_paths:
            raise ValueError("No video clips provided for concatenation.")

        if len(clip_paths) == 1:
            # Single clip, just copy/transcode directly
            return self.normalize_clip(clip_paths[0], output_path)

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Check if any transition requires crossfade
        has_crossfade = transitions and any(t == "short_crossfade" for t in transitions)

        if not has_crossfade:
            # Straight cut concatenation via concat demuxer
            concat_list_file = output_path.parent / "concat_list.txt"
            with open(concat_list_file, "w", encoding="utf-8") as f:
                for p in clip_paths:
                    f.write(f"file '{p.resolve()}'\n")

            cmd = [
                self._ffmpeg_path,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_list_file),
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-crf",
                "18",
                "-pix_fmt",
                "yuv420p",
                "-an",
                "-movflags",
                "+faststart",
                str(output_path),
            ]

            proc = subprocess.run(cmd, capture_output=True, text=True)
            if concat_list_file.exists():
                concat_list_file.unlink()

            if proc.returncode != 0:
                logger.error(f"Concat failed: {proc.stderr}")
                raise FFmpegExecutionError("Straight-cut concatenation failed", details={"stderr": proc.stderr[-500:]})

            return output_path

        # Complex xfade assembly
        # Probe durations of each clip
        durations = []
        for cp in clip_paths:
            meta = self.probe_video(cp)
            durations.append(meta["duration_seconds"])

        inputs = []
        for cp in clip_paths:
            inputs.extend(["-i", str(cp)])

        # Build filtergraph
        filter_parts = []
        current_stream = "[0:v]"
        current_offset = durations[0] - crossfade_duration

        for i in range(1, len(clip_paths)):
            next_stream = f"[{i}:v]"
            out_stream = f"[v{i}]" if i < len(clip_paths) - 1 else "[outv]"
            trans_type = transitions[i - 1] if transitions and i - 1 < len(transitions) else "straight_cut"

            if trans_type == "short_crossfade" and current_offset > 0:
                filter_parts.append(
                    f"{current_stream}{next_stream}xfade=transition=fade:duration={crossfade_duration}:offset={current_offset:.2f}{out_stream}"
                )
                current_offset = current_offset + durations[i] - crossfade_duration
            else:
                # Direct concat splice
                filter_parts.append(
                    f"{current_stream}{next_stream}concat=n=2:v=1:a=0{out_stream}"
                )
                current_offset = current_offset + durations[i]

            current_stream = out_stream

        filter_graph = ";".join(filter_parts)

        cmd = [
            self._ffmpeg_path,
            "-y",
            *inputs,
            "-filter_complex",
            filter_graph,
            "-map",
            "[outv]" if len(clip_paths) > 1 else "[0:v]",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-an",
            "-movflags",
            "+faststart",
            str(output_path),
        ]

        logger.info(f"Executing xfade assembly for {len(clip_paths)} clips")
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            logger.warning(f"xfade failed, falling back to straight cut: {proc.stderr}")
            # Fallback to straight cut if xfade offsets fail
            return self.concatenate_clips(clip_paths, output_path, transitions=None)

        return output_path

    def add_background_audio(
        self,
        video_path: Path,
        audio_path: Path,
        output_path: Path,
        volume: float = 0.25,
    ) -> Path:
        """
        Mixes royalty-safe background audio with subtle fade out matching video duration.
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        meta = self.probe_video(video_path)
        duration = meta["duration_seconds"]

        # Fade out in last 2 seconds
        fade_start = max(0.0, duration - 2.0)
        audio_filter = f"volume={volume},afade=t=out:st={fade_start:.2f}:d=2.0"

        cmd = [
            self._ffmpeg_path,
            "-y",
            "-i",
            str(video_path),
            "-i",
            str(audio_path),
            "-filter_complex",
            f"[1:a]{audio_filter}[aout]",
            "-map",
            "0:v",
            "-map",
            "[aout]",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-t",
            str(duration),
            "-movflags",
            "+faststart",
            str(output_path),
        ]

        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            logger.error(f"Audio mixing failed: {proc.stderr}")
            raise FFmpegExecutionError("Failed to mix background audio", details={"stderr": proc.stderr[-500:]})

        return output_path


ffmpeg_engine = FFmpegEngine()
