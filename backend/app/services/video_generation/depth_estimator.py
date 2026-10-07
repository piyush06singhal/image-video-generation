"""Monocular depth estimation, used to turn a flat photograph into a 2.5D shot.

The single biggest reason a camera move over a still reads as "a slideshow with
motion" is that *everything in the frame moves together*. Real footage does not
work that way: when a camera pushes in, the lamp moves more than the wall behind
it, and the parallax between those two planes is what the eye reads as depth.

This module supplies the missing ingredient — a per-pixel depth estimate — so the
Ken Burns renderer can move near pixels and far pixels by different amounts. The
model is Depth Anything V2 (Small) exported to ONNX, run locally on CPU through
onnxruntime: no network call, no quota, no cost, and the source pixels are still
the real photograph, so accuracy is preserved.

Everything here is optional by design. If onnxruntime is not installed or the
model file is absent, :func:`estimate_depth` returns ``None`` and the renderer
falls back to its flat affine camera — a worse-looking shot, but never a broken
render.
"""

from pathlib import Path
import threading
from typing import Optional, Tuple

import cv2
import numpy as np

from app.core.logging import logger

# ImageNet statistics — the normalisation the Depth Anything checkpoints were
# trained with. Getting these wrong silently produces a plausible-looking but
# wrong depth map, so they are named rather than inlined.
_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)

# Depth Anything's ViT backbone requires an input whose sides are multiples of 14.
_PATCH = 14
_DEFAULT_SIZE = 518  # 518 = 37 * 14, the resolution the model is usually run at.


def default_model_path() -> Path:
    """Where the depth checkpoint is expected to live by default."""
    return Path(__file__).resolve().parents[3] / "models" / "depth_anything_v2_small.onnx"


class DepthEstimator:
    """Lazily-loaded, cached ONNX depth model.

    The session is built on first use and reused for the life of the process,
    because loading a ~100MB graph per scene would dominate render time.
    """

    def __init__(self, model_path: Optional[Path] = None, input_size: int = _DEFAULT_SIZE):
        self._model_path = Path(model_path) if model_path else default_model_path()
        self._input_size = int(input_size)
        self._session = None  # onnxruntime.InferenceSession | False (unavailable)
        self._lock = threading.Lock()
        self._warned = False

    # ── session management ───────────────────────────────────────────────
    @property
    def model_path(self) -> Path:
        return self._model_path

    def _load(self):
        """Builds the inference session once; ``False`` caches a hard failure."""
        if self._session is not None:
            return self._session
        with self._lock:
            if self._session is not None:
                return self._session
            if not self._model_path.exists():
                self._warn_once(
                    f"Depth model not found at {self._model_path}; "
                    "2.5D parallax disabled, falling back to a flat camera move."
                )
                self._session = False
                return self._session
            try:
                import onnxruntime as ort

                opts = ort.SessionOptions()
                # Depth estimation is a small vision transformer on CPU; letting it
                # use every core keeps a scene clip to well under a second per frame.
                opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
                opts.intra_op_num_threads = 0
                self._session = ort.InferenceSession(
                    str(self._model_path),
                    sess_options=opts,
                    providers=["CPUExecutionProvider"],
                )
                logger.info(f"Depth model loaded: {self._model_path.name}")
            except Exception as exc:  # noqa: BLE001 - any failure means "no depth"
                self._warn_once(f"Depth model unavailable ({exc}); using a flat camera move.")
                self._session = False
            return self._session

    def _warn_once(self, message: str) -> None:
        if not self._warned:
            logger.warning(f"[depth] {message}")
            self._warned = True

    def is_available(self) -> bool:
        """True when depth can actually be produced (model present + runtime ok)."""
        return self._load() is not False

    # ── inference ────────────────────────────────────────────────────────
    def _preprocess(self, image_bgr: np.ndarray) -> Tuple[np.ndarray, Tuple[int, int]]:
        """BGR uint8 image -> (NCHW float32 RGB tensor, (h, w) fed to the model)."""
        rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        size = self._input_size - (self._input_size % _PATCH)
        resized = cv2.resize(rgb, (size, size), interpolation=cv2.INTER_CUBIC)
        arr = resized.astype(np.float32) / 255.0
        arr = (arr - _MEAN) / _STD
        tensor = np.transpose(arr, (2, 0, 1))[None, ...]
        return np.ascontiguousarray(tensor, dtype=np.float32), (size, size)

    def estimate(self, image_bgr: np.ndarray) -> Optional[np.ndarray]:
        """Returns a float32 depth map in ``[0, 1]`` matching the image's size.

        ``1.0`` is the *nearest* part of the frame and ``0.0`` the furthest, which
        is the convention the renderer's parallax maths expects. Returns ``None``
        when depth is unavailable so callers can degrade instead of failing.
        """
        session = self._load()
        if session is False or session is None:
            return None
        if image_bgr is None or image_bgr.size == 0:
            return None

        try:
            tensor, _ = self._preprocess(image_bgr)
            inp = session.get_inputs()[0]
            out_name = session.get_outputs()[0].name
            raw = session.run([out_name], {inp.name: tensor})[0]
        except Exception as exc:  # noqa: BLE001
            self._warn_once(f"Depth inference failed ({exc}); using a flat camera move.")
            return None

        depth = np.asarray(raw, dtype=np.float32).squeeze()
        if depth.ndim != 2 or depth.size == 0:
            return None

        h, w = image_bgr.shape[:2]

        # Depth Anything emits *relative inverse* depth: larger means closer.
        # Rescale robustly on percentiles rather than min/max so a single blown
        # highlight cannot squash the whole range into a flat plane.
        lo, hi = np.percentile(depth, 2.0), np.percentile(depth, 98.0)
        if hi - lo < 1e-6:
            return None
        depth = np.clip((depth - lo) / (hi - lo), 0.0, 1.0)

        # A little gamma spreads the useful range: interior photos cluster their
        # depth near the far end, which would otherwise give almost no parallax.
        depth = np.power(depth, 0.75)

        # Bicubic upsampling can overshoot the [0, 1] range, so clip again after
        # the resize — the parallax maths assumes a bounded deviation.
        return np.clip(cv2.resize(depth, (w, h), interpolation=cv2.INTER_CUBIC), 0.0, 1.0)


def smooth_depth(depth: np.ndarray, image_bgr: np.ndarray, strength: float = 1.0) -> np.ndarray:
    """Edge-preserving smoothing of a depth map before it drives a warp.

    Raw network depth is noisy at the pixel level, and any noise in the warp
    field shows up as a shimmering "boiling" artefact that is far more distracting
    than no parallax at all. Bilateral filtering keeps real object boundaries
    (the strong edges) while flattening the noise inside each surface.

    ``image_bgr`` is accepted as the intended edge guide for a joint filter; the
    separable bilateral pass below is used instead because OpenCV's joint
    ``guidedFilter`` lives in the non-free ``ximgproc`` module, which is not
    guaranteed to be present.
    """
    if depth is None:
        return depth
    d = depth.astype(np.float32)
    d = cv2.bilateralFilter(d, d=9, sigmaColor=0.08, sigmaSpace=9)
    d = cv2.bilateralFilter(d, d=0, sigmaColor=0.10 * strength + 0.06, sigmaSpace=13)
    return np.clip(d, 0.0, 1.0)


# Process-wide estimator. The renderer uses this instance unless a caller injects
# its own (which the tests do, so they never depend on the model being on disk).
depth_estimator = DepthEstimator()
