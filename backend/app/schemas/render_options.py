"""User-facing cinematic render options.

Phase 4/5 used to be entirely hardcoded: every walkthrough was 1920x1080 @ 24fps,
one fixed motion preset per scene, 0.35-0.4s crossfades on a couple of cuts, an
optional (and unimplemented) title card, and silence. This module is the single
contract that makes the look configurable end-to-end — the studio UI collects it,
the API persists it per project, the generation providers honour the motion /
duration / resolution parts, and the assembler honours the grading, transitions,
overlays, music and output format parts.
"""

import hashlib
import json
from enum import Enum
from typing import Any, Dict, Optional, Tuple

from pydantic import BaseModel, Field, field_validator


class MotionIntensity(str, Enum):
    """How far the virtual camera travels over each photograph."""

    SUBTLE = "subtle"
    BALANCED = "balanced"
    BOLD = "bold"


class TransitionStyle(str, Enum):
    """Inter-scene transition applied between every pair of clips.

    ``BLUR_DISSOLVE`` and ``SMOOTH_LEFT`` are motion-bridged cuts: instead of
    simply mixing two stills, they smear the outgoing frame as the incoming one
    arrives, which disguises the fact that the camera restarts on every room and
    is the single cheapest way to make a tour feel continuously shot.
    """

    STRAIGHT_CUT = "straight_cut"
    CROSSFADE = "crossfade"
    FADE_TO_BLACK = "fade_to_black"
    SLIDE_LEFT = "slide_left"
    WIPE_UP = "wipe_up"
    BLUR_DISSOLVE = "blur_dissolve"
    SMOOTH_LEFT = "smooth_left"


class ColorGrade(str, Enum):
    """Cinematic colour treatment applied to the assembled walkthrough."""

    NONE = "none"
    WARM_LUXURY = "warm_luxury"
    GOLDEN_HOUR = "golden_hour"
    COOL_MODERN = "cool_modern"
    CINEMATIC_TEAL = "cinematic_teal"
    NOIR = "noir"


class AspectRatio(str, Enum):
    """Output frame shape."""

    LANDSCAPE = "16:9"
    VERTICAL = "9:16"
    SQUARE = "1:1"


class MusicStyle(str, Enum):
    """Procedurally synthesised royalty-free score (no licensed assets shipped)."""

    NONE = "none"
    AMBIENT = "ambient"
    UPLIFTING = "uplifting"
    MINIMAL_PIANO = "minimal_piano"


# Base *landscape* (16:9) dimensions per quality tier. The other aspect ratios are
# derived from these so a single "resolution" choice stays meaningful in portrait
# and square reels too.
RESOLUTION_PRESETS: Dict[str, Tuple[int, int]] = {
    "720p": (1280, 720),
    "1080p": (1920, 1080),
    "1440p": (2560, 1440),
}

# JSON2Video names a few of the standard frames outright; anything else is sent as
# `resolution: "custom"` with explicit width/height (the docs allow 50-3840).
JSON2VIDEO_NAMED_SIZES: Dict[Tuple[int, int], str] = {
    (1280, 720): "hd",
    (1920, 1080): "full-hd",
    (1080, 1920): "instagram-story",
    (1080, 1080): "squared",
}


def target_dimensions(aspect_ratio: "AspectRatio", resolution: str) -> Tuple[int, int]:
    """Resolve an (aspect_ratio, resolution) pair into concrete pixel dimensions.

    Landscape keeps the tier's full frame; portrait and square are built off the
    tier's *short* side so text and detail stay crisp on phones.
    """
    base_w, base_h = RESOLUTION_PRESETS.get(resolution, RESOLUTION_PRESETS["1080p"])
    short = base_h
    if aspect_ratio == AspectRatio.VERTICAL:
        return short, short * 16 // 9
    if aspect_ratio == AspectRatio.SQUARE:
        return short, short
    return base_w, base_h


def _even(value: int) -> int:
    """H.264 requires even dimensions."""
    return value if value % 2 == 0 else value + 1


class RenderOptions(BaseModel):
    """Complete creative configuration for a walkthrough render.

    Defaults describe the "Cinematic Luxury" house style: warm grade, gentle
    push-ins with per-room variety, soft crossfades, an intro and outro card,
    room labels, subtle vignette and grain, and an ambient score.
    """

    preset: str = Field(default="cinematic_luxury", description="Style preset these values came from")

    # ── Motion & pacing ───────────────────────────────────────────────
    scene_duration_seconds: float = Field(
        default=4.5, ge=2.0, le=12.0, description="Target duration of every scene clip"
    )
    motion_intensity: MotionIntensity = Field(
        default=MotionIntensity.BALANCED, description="Travel distance of the virtual camera"
    )
    camera_variety: bool = Field(
        default=True,
        description="Assign a different cinematic move to each consecutive room instead of repeating one",
    )
    depth_parallax: bool = Field(
        default=True,
        description=(
            "Estimate per-pixel depth and move near pixels further than far pixels, so the shot "
            "has real dimensionality instead of the whole frame sliding as one sheet"
        ),
    )
    motion_blur: bool = Field(
        default=True,
        description="Accumulate a trailing-shutter blur on fast movement, the way a real camera does",
    )

    # ── Transitions ───────────────────────────────────────────────────
    transition_style: TransitionStyle = Field(
        default=TransitionStyle.CROSSFADE, description="Transition used between all scenes"
    )
    transition_duration_seconds: float = Field(
        default=0.7, ge=0.2, le=2.0, description="Length of each inter-scene transition"
    )

    # ── Output format ─────────────────────────────────────────────────
    aspect_ratio: AspectRatio = Field(default=AspectRatio.LANDSCAPE, description="Output frame shape")
    resolution: str = Field(default="1080p", description="Output quality tier: 720p / 1080p / 1440p")
    fps: int = Field(default=30, ge=12, le=60, description="Output frames per second")

    # ── Titles & overlays ─────────────────────────────────────────────
    intro_title_enabled: bool = Field(default=True, description="Open on a branded title card")
    intro_title_text: Optional[str] = Field(
        default=None, description="Override the intro headline; defaults to the project name"
    )
    # Cards are kept short on purpose: every second spent on a title card is a
    # second not spent showing the property. 2.5s each once meant a fifth of a
    # 19s tour was graphics.
    intro_duration_seconds: float = Field(default=2.2, ge=1.0, le=6.0, description="Intro card duration")
    outro_enabled: bool = Field(default=True, description="Close on a branded end card")
    outro_duration_seconds: float = Field(default=2.2, ge=1.0, le=6.0, description="End card duration")
    outro_text: Optional[str] = Field(default=None, description="Override the end-card headline")
    room_labels_enabled: bool = Field(
        default=True, description="Burn a lower-third room name onto each scene"
    )
    room_counter: bool = Field(
        default=True,
        description="Add a room position counter and tour progress line to each lower-third",
    )
    brand_text: Optional[str] = Field(
        default=None,
        description="Short brand or agency mark shown discreetly on the title and end cards",
    )

    # ── Look ──────────────────────────────────────────────────────────
    color_grade: ColorGrade = Field(default=ColorGrade.WARM_LUXURY, description="Colour treatment")
    vignette: bool = Field(default=True, description="Subtle darkened corners for a lens feel")
    film_grain: bool = Field(default=True, description="Fine sensor grain so stills do not read as stills")
    cinematic_bloom: bool = Field(
        default=True,
        description=(
            "Highlight halation: only true highlights bloom, smeared wide the way a fast lens "
            "does. It warms the cut without lifting shadows into haze"
        ),
    )
    # Off by default on purpose. Bars look filmic on a movie screen, but on a
    # property listing they remove 11% of the picture the client is paying to see,
    # and a frame that is smaller *and* dimmer is exactly what reads as diluted.
    letterbox: bool = Field(
        default=False,
        description="Scope-style cinematic bars, landscape output only (removes picture area)",
    )

    # ── Music ─────────────────────────────────────────────────────────
    music_enabled: bool = Field(default=True, description="Add a synthesised background score")
    music_style: MusicStyle = Field(default=MusicStyle.AMBIENT, description="Score mood")
    # Applied once, at the mix stage. It used to be applied twice (composer *and*
    # mix), which made the default 0.28 an effective 0.078 — the reason the score
    # was effectively inaudible in earlier renders.
    music_volume: float = Field(default=0.60, ge=0.0, le=1.0, description="Score volume relative to full scale")

    @field_validator("resolution")
    @classmethod
    def validate_resolution(cls, v: str) -> str:
        if v not in RESOLUTION_PRESETS:
            raise ValueError(f"resolution must be one of {sorted(RESOLUTION_PRESETS)}")
        return v

    def dimensions(self) -> Tuple[int, int]:
        """Concrete, even (width, height) for this option set."""
        w, h = target_dimensions(self.aspect_ratio, self.resolution)
        return _even(w), _even(h)

    def effective_aspect_value(self) -> str:
        return self.aspect_ratio.value

    # ── change detection ──────────────────────────────────────────────
    # Two signatures so the UI can distinguish "your clips are now the wrong
    # length or shape" (expensive: needs regeneration) from "the final cut would
    # look different" (cheap: just reassemble). Without this, changing settings in
    # the UI silently left the previously rendered video in place.
    def generation_signature(self) -> str:
        """Fingerprint of the options that change the *pixels of each clip*."""
        payload = {
            "duration": round(float(self.scene_duration_seconds), 3),
            "aspect": self.aspect_ratio.value,
            "resolution": self.resolution,
            "fps": self.fps,
            "motion_intensity": self.motion_intensity.value,
            "camera_variety": self.camera_variety,
            # Both of these are baked into the rendered clip, so turning either on
            # or off genuinely invalidates existing clips.
            "depth_parallax": self.depth_parallax,
            "motion_blur": self.motion_blur,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:12]

    def assembly_signature(self) -> str:
        """Fingerprint of every option that affects the *final assembled cut*."""
        return hashlib.sha256(
            json.dumps(self.model_dump(mode="json"), sort_keys=True).encode()
        ).hexdigest()[:12]

    def provider_hints(self, scene_index: int = 0) -> Dict[str, Any]:
        """Flattens the options into the dict shape image-to-video providers consume.

        Keeping this mapping in one place means the Ken Burns renderer and the
        cloud renderer are driven by exactly the same contract, and adding a new
        option only requires touching this method plus the provider that reads it.
        """
        width, height = self.dimensions()
        return {
            "motion_intensity": self.motion_intensity.value,
            "camera_variety": self.camera_variety,
            "depth_parallax": self.depth_parallax,
            "motion_blur": self.motion_blur,
            "scene_index": scene_index,
            "width": width,
            "height": height,
            "fps": self.fps,
            "duration_seconds": self.scene_duration_seconds,
            "aspect_ratio": self.aspect_ratio.value,
            "resolution": self.resolution,
        }


# ── Presets ───────────────────────────────────────────────────────────────
# Each preset is a full option set so the UI can apply one atomically and users
# can then tweak individual controls without losing coherence.
PRESET_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "cinematic_luxury": dict(
        label="Cinematic Luxury",
        description="Slow warm push-ins, soft crossfades, ambient score. The flagship listing look.",
        options=dict(
            motion_intensity=MotionIntensity.BALANCED,
            scene_duration_seconds=4.5,
            transition_style=TransitionStyle.CROSSFADE,
            transition_duration_seconds=0.6,
            color_grade=ColorGrade.WARM_LUXURY,
            vignette=True,
            film_grain=True,
            music_enabled=True,
            music_style=MusicStyle.AMBIENT,
            room_labels_enabled=True,
            room_counter=True,
            depth_parallax=True,
            motion_blur=True,
            cinematic_bloom=True,
            letterbox=False,
            intro_title_enabled=True,
            outro_enabled=True,
            fps=30,
        ),
    ),
    "modern_minimal": dict(
        label="Modern Minimal",
        description="Clean, cooler grade with restrained motion and a minimal piano bed. No grain.",
        options=dict(
            motion_intensity=MotionIntensity.SUBTLE,
            scene_duration_seconds=4.0,
            transition_style=TransitionStyle.CROSSFADE,
            transition_duration_seconds=0.5,
            color_grade=ColorGrade.COOL_MODERN,
            vignette=False,
            film_grain=False,
            music_enabled=True,
            music_style=MusicStyle.MINIMAL_PIANO,
            room_labels_enabled=True,
            room_counter=True,
            depth_parallax=True,
            motion_blur=True,
            cinematic_bloom=False,
            letterbox=False,
            intro_title_enabled=True,
            outro_enabled=False,
            fps=30,
        ),
    ),
    "energetic_reel": dict(
        label="Energetic Vertical Reel",
        description="9:16 for Instagram/TikTok/Shorts. Faster cuts, bolder motion, uplifting score.",
        options=dict(
            aspect_ratio=AspectRatio.VERTICAL,
            motion_intensity=MotionIntensity.BOLD,
            scene_duration_seconds=3.0,
            transition_style=TransitionStyle.SLIDE_LEFT,
            transition_duration_seconds=0.4,
            color_grade=ColorGrade.CINEMATIC_TEAL,
            vignette=True,
            film_grain=True,
            music_enabled=True,
            music_style=MusicStyle.UPLIFTING,
            room_labels_enabled=True,
            room_counter=True,
            depth_parallax=True,
            motion_blur=True,
            cinematic_bloom=True,
            letterbox=False,
            intro_title_enabled=True,
            outro_enabled=True,
            fps=30,
        ),
    ),
    "documentary_tour": dict(
        label="Documentary Tour",
        description="Longer, unhurried shots that read like a hosted walkthrough. Natural colour, no music.",
        options=dict(
            motion_intensity=MotionIntensity.SUBTLE,
            scene_duration_seconds=6.0,
            transition_style=TransitionStyle.CROSSFADE,
            transition_duration_seconds=0.5,
            color_grade=ColorGrade.NONE,
            vignette=False,
            film_grain=False,
            music_enabled=False,
            music_style=MusicStyle.NONE,
            room_labels_enabled=True,
            room_counter=False,
            depth_parallax=True,
            motion_blur=True,
            cinematic_bloom=False,
            letterbox=False,
            intro_title_enabled=True,
            outro_enabled=False,
            fps=24,
        ),
    ),
    "quick_draft": dict(
        label="Quick Draft",
        description="Fast, unpolished preview to sanity-check ordering before committing to a full render.",
        options=dict(
            motion_intensity=MotionIntensity.SUBTLE,
            scene_duration_seconds=3.0,
            transition_style=TransitionStyle.STRAIGHT_CUT,
            transition_duration_seconds=0.3,
            color_grade=ColorGrade.NONE,
            vignette=False,
            film_grain=False,
            music_enabled=False,
            music_style=MusicStyle.NONE,
            room_labels_enabled=False,
            room_counter=False,
            # A draft exists to check ordering cheaply, so the expensive image
            # work (depth inference, motion-blur accumulation, the bloom pass) is
            # off and a preview renders in a fraction of the time.
            depth_parallax=False,
            motion_blur=False,
            cinematic_bloom=False,
            letterbox=False,
            intro_title_enabled=False,
            outro_enabled=False,
            resolution="720p",
            fps=24,
        ),
    ),
}


def build_render_options(preset: Optional[str], overrides: Optional[Dict[str, Any]] = None) -> RenderOptions:
    """Instantiate options from a preset name plus per-field overrides."""
    name = preset or "cinematic_luxury"
    definition = PRESET_DEFINITIONS.get(name)
    if definition is None:
        raise ValueError(f"Unknown render preset '{name}'. Valid presets: {sorted(PRESET_DEFINITIONS)}")
    payload: Dict[str, Any] = {"preset": name, **definition["options"]}
    if overrides:
        payload.update({k: v for k, v in overrides.items() if v is not None})
    return RenderOptions(**payload)


def default_render_options() -> RenderOptions:
    return build_render_options("cinematic_luxury")


class RenderOptionsUpdate(BaseModel):
    """Partial update payload for the render-options endpoint.

    Sending only ``options`` merges onto the saved settings, so the studio can
    PATCH the one control the user moved without echoing the whole form back.
    Sending ``preset`` re-bases the whole option set, because picking a preset is
    an explicit "make it look like this" action.
    """

    preset: Optional[str] = Field(
        default=None, description="Style preset to apply; replaces all other values"
    )
    options: Optional[Dict[str, Any]] = Field(
        default=None, description="Partial field overrides merged onto the current options"
    )
    replace: bool = Field(
        default=False, description="When true, unspecified fields reset to the house style"
    )


class RenderPresetInfo(BaseModel):
    """Lightweight preset descriptor for the studio UI."""

    id: str
    label: str
    description: str
    options: Dict[str, Any]
    recommended: bool = False
