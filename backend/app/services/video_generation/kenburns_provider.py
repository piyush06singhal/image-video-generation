"""Fully local, deterministic image-to-video provider.

Instead of *hallucinating* a video with a diffusion model, this provider renders a
genuine cinematic camera move over the real source photograph. Accuracy is
guaranteed — the pixels are the actual property, so furniture, wall positions,
window counts and finishes can never drift or mutate, which is the single biggest
failure mode of diffusion I2V on interiors. There is also no API, no quota and no
cost, and the output is deterministic.

The hard part is that a flat pan over a photograph looks like a slideshow. Three
things fix that here, and together they are what makes the shot read as footage:

* **2.5D depth parallax.** A monocular depth model (Depth Anything V2 Small, run
  locally through onnxruntime) estimates how far away each pixel is. The camera
  then moves near pixels further than far pixels — the same relative slide between
  a lamp and the wall behind it that a real dolly produces. Without this,
  everything in the frame moves as one rigid sheet, which is exactly the effect
  users read as "basic".
* **Motion blur.** Real footage blurs during fast movement. Frames are accumulated
  over a trailing shutter window, which softens the smeary regions that
  depth-warping leaves behind and is one of the strongest "this is a camera, not a
  still" cues.
* **Camera craft.** A hold → accelerate → settle ease, a per-room variety rotation,
  an arced travel path, and a sub-pixel handheld sway, so no two rooms get the same
  move and nothing runs at constant speed.

Everything degrades safely: if the depth model or onnxruntime is unavailable the
renderer falls back to the flat affine camera rather than failing a render.
"""

from pathlib import Path
import os
import tempfile
from typing import Any, Dict, Optional, Tuple

import cv2
import numpy as np

from app.core.config import settings
from app.core.errors import AppException
from app.core.logging import logger
from app.services.video_generation.base import ImageToVideoProvider, ProviderResult
from app.services.video_generation.depth_estimator import DepthEstimator, smooth_depth
from app.services.video_assembler.ffmpeg_engine import ffmpeg_engine


def _clamp01(t: float) -> float:
    return max(0.0, min(1.0, t))


def _cinematic_progress(t: float) -> float:
    """An almost-immediate, gently decelerating travel.

    This used to compress the ease into the middle 80% of the clip, which parked
    the camera for the first tenth and the last tenth of every shot. That reads as
    a stalled slideshow: the eye settles, then the picture lurches, then it stops
    again — and because the stall lands right next to the crossfade it makes the
    whole cut feel stop-start. Instead the camera leaves almost at once and spends
    the shot bleeding off speed, which is what a hand-operated move looks like.
    """
    inner = _clamp01((_clamp01(t) - 0.04) / 0.92)
    return inner * inner * (3.0 - 2.0 * inner)


# Camera choreography library.
#   zoom_start, zoom_end, (drift_x, drift_y) in normalised source units, arc
# ``arc`` bows the travel path perpendicular to the drift direction.
# Values are tuned so that at "balanced" intensity the move is a clear but
# unhurried glide; the intensity multiplier scales drift and zoom range together.
_MOVE_LIBRARY: Dict[str, Tuple[float, float, Tuple[float, float], float]] = {
    "push_in_settle": (1.02, 1.22, (0.000, -0.016), 0.000),
    "pull_back_reveal": (1.24, 1.03, (0.000, 0.014), 0.000),
    "glide_left": (1.16, 1.16, (-0.135, 0.000), 0.014),
    "glide_right": (1.16, 1.16, (0.135, 0.000), -0.014),
    "arc_orbit": (1.12, 1.19, (0.095, -0.038), 0.065),
    "tilt_up": (1.11, 1.15, (0.000, -0.075), 0.012),
    "slow_creep": (1.04, 1.13, (0.045, -0.016), 0.022),
}

# Rotation used when the project asks for camera variety. The order deliberately
# alternates direction and depth so no two consecutive rooms feel the same.
_VARIETY_ORDER = [
    "glide_left",
    "push_in_settle",
    "pull_back_reveal",
    "arc_orbit",
    "glide_right",
    "tilt_up",
    "slow_creep",
]

_MOTION_TO_MOVE: Dict[str, str] = {
    "slow_forward": "push_in_settle",
    "exterior_forward": "push_in_settle",
    "slight_dolly": "push_in_settle",
    "slow_backward": "pull_back_reveal",
    "pan_left": "glide_left",
    "pan_right": "glide_right",
    "gentle_orbit": "arc_orbit",
    "static_subtle_motion": "slow_creep",
}

_INTENSITY_SCALE = {"subtle": 0.60, "balanced": 1.00, "bold": 1.55}

# Weighted samples across a trailing shutter window. Three taps is enough to read
# as blur without tripling the render cost of a five-tap version.
_SHUTTER_WEIGHTS = ((0.00, 0.45), (0.50, 0.35), (1.00, 0.20))

# Upper bound on the extra framing zoom the parallax is allowed to buy itself. A
# hard cap keeps a low-resolution source from being blown up into mush.
_MAX_OVERSCAN = 1.35


class KenBurnsProvider(ImageToVideoProvider):
    """Local provider that turns a still photograph into cinematic camera motion."""

    def __init__(
        self,
        width: Optional[int] = None,
        height: Optional[int] = None,
        fps: Optional[float] = None,
        depth_estimator: Optional[DepthEstimator] = None,
    ):
        self.width = int(width or settings.KENBURNS_WIDTH)
        self.height = int(height or settings.KENBURNS_HEIGHT)
        self.fps = float(fps or settings.KENBURNS_FPS)
        # Injectable so tests can exercise the flat path without the model on disk.
        self._depth_estimator = depth_estimator or DepthEstimator(
            model_path=settings.DEPTH_MODEL_PATH or None
        )
        # Recorded on each result so the UI can tell whether a render was 2.5D.
        self._last_depth_used = False

    def get_provider_name(self) -> str:
        return "local_kenburns"

    def get_model_name(self) -> str:
        return "cinematic-affine-2.5d"

    # ── Motion choreography ──────────────────────────────────────────────
    @staticmethod
    def _select_move(
        camera_motion: str, intensity: str, variety: bool, scene_index: int
    ) -> Tuple[str, float, float, float, float, float]:
        """Resolves the move for one scene.

        Returns (move_name, zoom_start, zoom_end, drift_x, drift_y, arc).
        """
        motion = (camera_motion or "").strip().lower()
        preferred = _MOTION_TO_MOVE.get(motion, "slow_creep")

        if variety and scene_index > 0:
            move_name = _VARIETY_ORDER[(scene_index - 1) % len(_VARIETY_ORDER)]
        else:
            move_name = preferred

        z0, z1, (dx, dy), arc = _MOVE_LIBRARY[move_name]
        scale = _INTENSITY_SCALE.get(intensity, 1.0)

        # Scale the *travel* rather than the whole zoom level: the base crop
        # overscan stays fixed, so every intensity still reads as a lens move
        # instead of a progressively tighter crop.
        base = min(z0, z1)
        z0 = base + (z0 - base) * scale
        z1 = base + (z1 - base) * scale
        return move_name, z0, z1, dx * scale, dy * scale, arc * scale

    # ── shared choreography maths ────────────────────────────────────────
    @staticmethod
    def _camera_at(
        t: float,
        z0: float,
        z1: float,
        drift_x: float,
        drift_y: float,
        arc: float,
        sway_amp: float,
        phase: float,
    ) -> Tuple[float, float, float]:
        """Virtual camera state at clip progress ``t`` (0..1).

        Returns ``(cx_n, cy_n, zoom)`` — the normalised look-at point (which
        already includes the arced travel path and the handheld sway) and the zoom
        level. The look-at point is also what drives parallax, because parallax is
        proportional to how far the camera has actually translated.
        """
        e = _cinematic_progress(t)
        zoom = max(1.0, z0 + (z1 - z0) * e)

        px, py = -drift_y, drift_x
        if abs(drift_x) + abs(drift_y) < 1e-9:
            px, py = 0.0, 1.0
        bow = arc * float(np.sin(np.pi * e))

        # Two-tone float rather than a single sine. A lone sine is a perfectly
        # periodic wobble, and the eye reads that as machine motion; summing a
        # second, faster, weaker wave at a non-integer ratio makes the drift
        # quasi-periodic, which is what an operator's hands actually do. Both
        # terms are scaled by ``sway_amp`` so "subtle" still means subtle.
        sway_x = sway_amp * (
            0.62 * float(np.sin(2 * np.pi * 0.27 * t + phase))
            + 0.38 * float(np.sin(2 * np.pi * 0.43 * t + phase * 1.7))
        )
        sway_y = sway_amp * (
            0.60 * float(np.sin(2 * np.pi * 0.19 * t + phase + 1.2))
            + 0.40 * float(np.sin(2 * np.pi * 0.31 * t + phase * 1.3))
        )
        cx_n = 0.5 + drift_x * e + bow * px + sway_x
        cy_n = 0.5 + drift_y * e + bow * py + sway_y
        return cx_n, cy_n, zoom

    def _screen_depth(self, depth: np.ndarray, out_w: int, out_h: int) -> np.ndarray:
        """Cover-crops and smooths the depth map onto the output raster.

        The parallax maths runs in *screen* space: depth is sampled at the output
        pixel rather than the (moving) source pixel. Over the small travels used
        here the two agree closely, and it saves re-warping the depth map on every
        frame.
        """
        dh, dw = depth.shape[:2]
        cover = max(out_w / dw, out_h / dh)
        nw, nh = max(1, int(round(dw * cover))), max(1, int(round(dh * cover)))
        resized = cv2.resize(depth.astype(np.float32), (nw, nh), interpolation=cv2.INTER_LINEAR)
        x0 = max(0, (nw - out_w) // 2)
        y0 = max(0, (nh - out_h) // 2)
        cropped = resized[y0 : y0 + out_h, x0 : x0 + out_w]
        if cropped.shape[0] != out_h or cropped.shape[1] != out_w:
            cropped = cv2.resize(cropped, (out_w, out_h), interpolation=cv2.INTER_LINEAR)
        return cv2.GaussianBlur(cropped, (0, 0), max(1.0, min(out_w, out_h) * 0.0025))

    # ── 2.5D depth parallax renderer ─────────────────────────────────────
    def _render_frames_parallax(
        self,
        source: np.ndarray,
        depth: np.ndarray,
        auto: Tuple[str, float, float, float, float, float],
        n_frames: int,
        intensity: str,
        scene_index: int,
        motion_blur: Optional[bool] = None,
    ) -> list:
        """Renders the clip with depth-driven parallax and trailing-shutter blur."""
        move_name, z0, z1, drift_x, drift_y, arc = auto
        out_w, out_h = self.width, self.height
        img_h, img_w = source.shape[:2]
        cover0 = max(out_w / img_w, out_h / img_h)

        intensity_scale = _INTENSITY_SCALE.get(intensity, 1.0)
        lateral = max(0.0, float(settings.DEPTH_PARALLAX_STRENGTH)) * intensity_scale
        zoom_par = max(0.0, float(settings.DEPTH_ZOOM_PARALLAX)) * intensity_scale
        shutter = 0.0 if motion_blur is False else max(0.0, float(settings.MOTION_BLUR_SHUTTER))
        rack = max(0.0, min(1.0, float(settings.RACK_FOCUS_STRENGTH)))

        # Headroom the parallax needs on each side, in source pixels: the widest
        # lateral shift the near plane will make, plus the outward push from the
        # depth-proportional magnification. Overscanning *more* than this only
        # costs sharpness, because the extra zoom has to be upscaled back, so the
        # minimum sufficient factor is computed rather than a flat guess.
        max_off_x = abs(drift_x) + abs(arc) + 0.004
        max_off_y = abs(drift_y) + abs(arc) + 0.004
        need_x = lateral * max_off_x * img_w
        need_y = lateral * max_off_y * img_h
        zoom_delta = zoom_par * abs(max(z0, z1) - 1.0)
        vis_w0 = out_w / (cover0 * max(z0, z1))
        vis_h0 = out_h / (cover0 * max(z0, z1))
        need_x += zoom_delta * vis_w0 * 0.5
        need_y += zoom_delta * vis_h0 * 0.5

        def _overscan(span: float, vis: float, need: float) -> float:
            inner = span - 2.0 * need
            if inner <= 1.0:
                return _MAX_OVERSCAN
            return max(1.0, vis / inner)

        correction = min(
            _MAX_OVERSCAN,
            max(_overscan(img_w, vis_w0, need_x), _overscan(img_h, vis_h0, need_y)),
        )
        cover = cover0 * correction

        screen_depth = self._screen_depth(depth, out_w, out_h)
        d_ref = float(np.median(screen_depth))
        spread = float(np.percentile(screen_depth, 88) - np.percentile(screen_depth, 12)) * 0.5
        spread = max(0.06, spread)
        # Deviation from the reference plane: positive is nearer than average.
        dd = np.clip((screen_depth - d_ref) / spread, -1.0, 1.0).astype(np.float32)

        blurred_source = None
        if rack > 0.0:
            sigma = max(1.2, min(img_w, img_h) * 0.006)
            blurred_source = cv2.GaussianBlur(source, (0, 0), sigma)

        # Static output-space grids, in output pixels relative to the frame centre.
        u = (np.arange(out_w, dtype=np.float32) - out_w * 0.5)[None, :]
        v = (np.arange(out_h, dtype=np.float32) - out_h * 0.5)[:, None]

        sway_amp = 0.0026 * intensity_scale
        phase = (scene_index % 5) * 0.7
        dt = 1.0 / (n_frames - 1) if n_frames > 1 else 0.0

        frames = []
        for i in range(n_frames):
            t = i / (n_frames - 1) if n_frames > 1 else 0.0

            accum = np.zeros((out_h, out_w, 3), dtype=np.float32)
            total_weight = 0.0

            for offset, weight in _SHUTTER_WEIGHTS:
                if weight <= 0.0:
                    continue
                # Trailing shutter: the blur trails the motion rather than
                # straddling it, which is how a real focal-plane shutter behaves.
                ts = t - offset * shutter * dt
                if offset > 0.0 and (ts < 0.0 or dt <= 0.0):
                    continue
                ts = _clamp01(ts)
                cx_n, cy_n, zoom = self._camera_at(
                    ts, z0, z1, drift_x, drift_y, arc, sway_amp, phase
                )

                cx = cx_n * img_w
                cy = cy_n * img_h
                vis_w = out_w / (cover * zoom)
                vis_h = out_h / (cover * zoom)
                cx = min(max(cx, vis_w / 2.0), max(vis_w / 2.0, img_w - vis_w / 2.0))
                cy = min(max(cy, vis_h / 2.0), max(vis_h / 2.0, img_h - vis_h / 2.0))
                s = out_w / vis_w

                # Flat (reference-plane) sampling position for every output pixel.
                sx0 = cx + u / s
                sy0 = cy + v / s

                # Depth-proportional magnification: during a push-in a foreground
                # object grows faster than the wall behind it.
                m = 1.0 + zoom_par * (zoom - 1.0) * dd

                # Depth-proportional translation: the near plane slides further
                # than the far plane as the camera travels. Physical parallax is
                # proportional to how far the camera has actually moved from its
                # starting point, so the look-at offset is the driver.
                par_x = lateral * (cx_n - 0.5) * img_w
                par_y = lateral * (cy_n - 0.5) * img_h

                map_x = (cx + (sx0 - cx) * m + par_x * dd).astype(np.float32)
                map_y = (cy + (sy0 - cy) * m + par_y * dd).astype(np.float32)

                # Cubic rather than linear: the source photograph is almost always
                # being enlarged to the output raster here, and cubic is markedly
                # sharper on upscales — which matters, because the warp resamples
                # every pixel of every frame.
                warped = cv2.remap(
                    source, map_x, map_y, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
                )
                if rack > 0.0 and blurred_source is not None:
                    soft = cv2.remap(
                        blurred_source, map_x, map_y, cv2.INTER_CUBIC,
                        borderMode=cv2.BORDER_REPLICATE,
                    )
                    # Far plane softens, near plane stays crisp (a shallow-focus look).
                    farness = np.clip(-dd, 0.0, 1.0)[..., None] * rack
                    warped = (warped.astype(np.float32) * (1.0 - farness)
                              + soft.astype(np.float32) * farness).astype(np.uint8)

                accum += warped.astype(np.float32) * weight
                total_weight += weight

            if total_weight > 0.0:
                accum /= total_weight
            frames.append(np.clip(accum, 0, 255).astype(np.uint8))

        self._last_depth_used = True
        logger.info(
            f"[local_kenburns] move='{move_name}' intensity={intensity} variety_rot="
            f"{scene_index} depth_parallax=on lateral={lateral:.2f} zoom={zoom_par:.2f} "
            f"shutter={shutter:.2f} overscan={correction:.3f}"
        )
        return frames

    # ── flat affine renderer (fallback / depth unavailable) ──────────────
    def _render_frames_affine(
        self,
        source: np.ndarray,
        auto: Tuple[str, float, float, float, float, float],
        n_frames: int,
        intensity: str,
        scene_index: int,
    ) -> list:
        move_name, z0, z1, drift_x, drift_y, arc = auto
        out_w, out_h = self.width, self.height
        img_h, img_w = source.shape[:2]
        cover = max(out_w / img_w, out_h / img_h)

        sway_amp = 0.0026 * _INTENSITY_SCALE.get(intensity, 1.0)
        phase = (scene_index % 5) * 0.7

        frames = []
        for i in range(n_frames):
            t = i / (n_frames - 1) if n_frames > 1 else 0.0
            cx_n, cy_n, zoom = self._camera_at(
                t, z0, z1, drift_x, drift_y, arc, sway_amp, phase
            )

            cx = cx_n * img_w
            cy = cy_n * img_h
            vis_w = out_w / (cover * zoom)
            vis_h = out_h / (cover * zoom)
            cx = min(max(cx, vis_w / 2.0), img_w - vis_w / 2.0)
            cy = min(max(cy, vis_h / 2.0), img_h - vis_h / 2.0)

            scale = out_w / vis_w  # isotropic: vis_w/out_w == vis_h/out_h by construction
            matrix = np.array(
                [
                    [scale, 0.0, out_w / 2.0 - scale * cx],
                    [0.0, scale, out_h / 2.0 - scale * cy],
                ],
                dtype=np.float32,
            )
            frames.append(
                cv2.warpAffine(
                    source,
                    matrix,
                    (out_w, out_h),
                    flags=cv2.INTER_LINEAR,
                    borderMode=cv2.BORDER_REPLICATE,
                )
            )
        logger.info(
            f"[local_kenburns] move='{move_name}' intensity={intensity} "
            f"variety={scene_index} depth_parallax=off (flat affine camera)"
        )
        return frames

    def _render_frames(
        self,
        source_image_path: Path,
        camera_motion: str,
        n_frames: int,
        intensity: str = "balanced",
        variety: bool = False,
        scene_index: int = 0,
        depth_parallax: Optional[bool] = None,
        motion_blur: Optional[bool] = None,
    ) -> list:
        source = cv2.imread(str(source_image_path), cv2.IMREAD_COLOR)
        if source is None:
            raise AppException(
                code="SOURCE_IMAGE_ERROR",
                message=f"Unable to decode source property image: {source_image_path.name}",
                status_code=422,
            )

        auto = self._select_move(camera_motion, intensity, variety, scene_index)
        self._last_depth_used = False

        wanted = settings.DEPTH_PARALLAX_ENABLED if depth_parallax is None else bool(depth_parallax)
        if wanted:
            depth = self._depth_estimator.estimate(source)
            if depth is not None:
                depth = smooth_depth(depth, source)
                return self._render_frames_parallax(
                    source, depth, auto, n_frames, intensity, scene_index, motion_blur=motion_blur
                )

        return self._render_frames_affine(source, auto, n_frames, intensity, scene_index)

    async def generate_clip(
        self,
        source_image_path: Path,
        prompt: str,
        negative_prompt: Optional[str],
        duration_seconds: float,
        camera_motion: str,
        output_path: Path,
        options: Optional[Dict[str, Any]] = None,
    ) -> ProviderResult:
        options = options or {}
        if not source_image_path.exists():
            raise AppException(
                code="SOURCE_IMAGE_ERROR",
                message=f"Source property image file not found at: {source_image_path}",
                status_code=404,
            )

        # Render options win over the constructor/settings so a per-project choice
        # (e.g. a 9:16 reel at 30fps) is honoured without rebuilding the provider.
        width = int(options.get("width") or self.width)
        height = int(options.get("height") or self.height)
        fps = float(options.get("fps") or self.fps)
        intensity = str(options.get("motion_intensity") or "balanced")
        variety = bool(options.get("camera_variety", False))
        scene_index = int(options.get("scene_index") or 0)
        depth_parallax = options.get("depth_parallax")
        motion_blur = options.get("motion_blur")

        self.width, self.height, self.fps = width, height, fps

        duration = max(1.0, float(duration_seconds or 4.0))
        n_frames = max(2, int(round(duration * fps)))

        logger.info(
            f"[local_kenburns] Rendering {n_frames} frames ({duration:.1f}s @ {fps}fps, "
            f"{width}x{height}) for motion='{camera_motion}' from {source_image_path.name}"
        )

        frames = self._render_frames(
            source_image_path,
            camera_motion,
            n_frames,
            intensity=intensity,
            variety=variety,
            scene_index=scene_index,
            depth_parallax=depth_parallax,
            motion_blur=motion_blur,
        )
        depth_used = self._last_depth_used

        output_path.parent.mkdir(parents=True, exist_ok=True)
        raw_fd, raw_name = tempfile.mkstemp(suffix=".mp4", dir=str(output_path.parent))
        os.close(raw_fd)
        raw_path = Path(raw_name)

        writer = cv2.VideoWriter(
            str(raw_path),
            cv2.VideoWriter_fourcc(*"mp4v"),
            fps,
            (width, height),
        )
        if not writer.isOpened():
            raw_path.unlink(missing_ok=True)
            raise AppException(
                code="VIDEO_ENCODER_ERROR",
                message="Unable to initialize the local video encoder for the walkthrough clip.",
                status_code=500,
            )
        try:
            for frame in frames:
                writer.write(frame)
        finally:
            writer.release()

        try:
            ffmpeg_engine.normalize_clip(
                input_path=raw_path,
                output_path=output_path,
                target_width=width,
                target_height=height,
                target_fps=fps,
            )
        finally:
            raw_path.unlink(missing_ok=True)

        return ProviderResult(
            provider_job_id=f"local_{output_path.stem}",
            output_video_path=output_path,
            provider_name=self.get_provider_name(),
            model_name=self.get_model_name(),
            duration_seconds=duration,
            raw_metadata={
                "camera_motion": camera_motion,
                "motion_intensity": intensity,
                "camera_variety": variety,
                "frames": n_frames,
                "resolution": f"{width}x{height}",
                "fps": fps,
                "synthetic_pixels": False,
                "depth_parallax": depth_used,
                "motion_blur": bool(
                    depth_used and motion_blur is not False
                    and float(settings.MOTION_BLUR_SHUTTER) > 0
                ),
            },
        )
