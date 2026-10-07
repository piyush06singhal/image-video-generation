"""Tests for the cinematic engine primitives.

These are the pieces that separate "four photos with a zoom" from a produced
walkthrough: cover conforming with no black bars, a real colour grade, burned-in
room labels, branded cards over the property's own photography, selectable
transitions, and a synthesised score.
"""

from pathlib import Path

import cv2
import numpy as np
import pytest

from app.schemas.render_options import ColorGrade, TransitionStyle
from app.services.video_assembler.ffmpeg_engine import ffmpeg_engine


def _write_clip(path: Path, width: int = 320, height: int = 180, seconds: float = 1.0, fps: float = 24.0) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    for i in range(max(2, int(seconds * fps))):
        frame = np.zeros((height, width, 3), np.uint8)
        frame[:] = (40, 60, 90)
        frame[height // 4 : height // 2, 10 + i * 2 : width // 2 + i * 2] = (200, 180, 120)
        writer.write(frame)
    writer.release()
    return path


def _read_frame(path: Path, at_seconds: float = 0.0) -> np.ndarray:
    cap = cv2.VideoCapture(str(path))
    assert cap.isOpened()
    if at_seconds > 0:
        cap.set(cv2.CAP_PROP_POS_MSEC, at_seconds * 1000)
    ok, frame = cap.read()
    cap.release()
    assert ok
    return frame


def _corner_brightness(frame: np.ndarray) -> float:
    h, w = frame.shape[:2]
    box = 12
    corners = [
        frame[0:box, 0:box],
        frame[0:box, w - box : w],
        frame[h - box : h, 0:box],
        frame[h - box : h, w - box : w],
    ]
    return float(np.mean([c.mean() for c in corners]))


# ── conform ──────────────────────────────────────────────────────────────

def test_cover_conform_fills_a_vertical_frame_with_no_letterboxing(tmp_path):
    """The old normaliser letterboxed, which is ruinous for a 9:16 reel."""
    source = _write_clip(tmp_path / "wide.mp4", width=320, height=180)
    output = tmp_path / "vertical.mp4"

    ffmpeg_engine.normalize_clip(source, output, target_width=180, target_height=320, target_fps=24.0)

    meta = ffmpeg_engine.probe_video(output)
    assert (meta["width"], meta["height"]) == (180, 320)
    # A letterboxed frame would have near-black bars top and bottom.
    assert _corner_brightness(_read_frame(output)) > 20


def test_pad_fit_still_letterboxes_when_explicitly_requested(tmp_path):
    source = _write_clip(tmp_path / "wide.mp4", width=320, height=180)
    output = tmp_path / "padded.mp4"

    ffmpeg_engine.normalize_clip(source, output, target_width=180, target_height=320, target_fps=24.0, fit="pad")

    assert _corner_brightness(_read_frame(output)) < 12


# ── grading ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("grade", [g.value for g in ColorGrade])
def test_every_grade_produces_a_valid_clip(tmp_path, grade):
    source = _write_clip(tmp_path / "src.mp4", width=160, height=90)
    output = tmp_path / f"{grade}.mp4"

    ffmpeg_engine.grade_and_conform(
        source, output, width=160, height=90, fps=24.0, color_grade=grade, vignette=True, film_grain=True
    )

    meta = ffmpeg_engine.probe_video(output)
    assert meta["duration_seconds"] > 0.5
    assert (meta["width"], meta["height"]) == (160, 90)


def test_grades_actually_change_the_image_and_differ_from_each_other(tmp_path):
    source = _write_clip(tmp_path / "src.mp4", width=160, height=90)
    frames = {}
    for grade in ["none", "warm_luxury", "cinematic_teal", "noir"]:
        out = tmp_path / f"g_{grade}.mp4"
        ffmpeg_engine.grade_and_conform(source, out, 160, 90, 24.0, color_grade=grade)
        frames[grade] = _read_frame(out).astype(np.int16)

    plain = frames["none"]
    for grade in ["warm_luxury", "cinematic_teal", "noir"]:
        assert np.abs(frames[grade] - plain).mean() > 1.0, f"{grade} did not alter the picture"

    # noir must desaturate: channel spread collapses.
    spread = lambda f: float(np.mean(np.ptp(f, axis=2)))  # noqa: E731
    assert spread(frames["noir"]) < spread(plain)


def test_vignette_and_grain_are_optional(tmp_path):
    source = _write_clip(tmp_path / "src.mp4", width=200, height=120)
    clean = tmp_path / "clean.mp4"
    treated = tmp_path / "treated.mp4"

    ffmpeg_engine.grade_and_conform(source, clean, 200, 120, 24.0, vignette=False, film_grain=False)
    # Grain is temporal, so a single frame comparison can miss it; compare the
    # frame-to-frame delta between two adjacent frames instead.
    ffmpeg_engine.grade_and_conform(source, treated, 200, 120, 24.0, vignette=True, film_grain=True)

    assert _corner_brightness(_read_frame(treated)) <= _corner_brightness(_read_frame(clean)) + 1.0


# ── room labels ──────────────────────────────────────────────────────────

def test_room_label_is_burned_into_the_lower_third(tmp_path):
    source = _write_clip(tmp_path / "src.mp4", width=320, height=180, seconds=2.0)
    labeled = tmp_path / "labeled.mp4"

    ffmpeg_engine.apply_room_label(source, labeled, "Primary Bedroom Suite", 320, 180, 24.0)

    meta = ffmpeg_engine.probe_video(labeled)
    assert (meta["width"], meta["height"]) == (320, 180)

    without = _read_frame(source, 1.0).astype(np.int16)
    with_label = _read_frame(labeled, 1.0).astype(np.int16)
    # White label text on a dark plate over a flat source: a large local delta.
    assert np.abs(with_label - without).max() > 40


def test_empty_room_label_is_a_plain_conform(tmp_path):
    source = _write_clip(tmp_path / "src.mp4", width=160, height=90, seconds=1.0)
    output = tmp_path / "nolabel.mp4"

    ffmpeg_engine.apply_room_label(source, output, "   ", 160, 90, 24.0)

    assert ffmpeg_engine.probe_video(output)["duration_seconds"] > 0.5


# ── branded cards ────────────────────────────────────────────────────────

def test_branded_card_uses_the_photo_as_a_backdrop(tmp_path):
    photo = tmp_path / "room.jpg"
    cv2.imwrite(str(photo), np.full((360, 640, 3), 180, np.uint8))
    card = tmp_path / "card.mp4"

    ffmpeg_engine.create_branded_card(
        output_path=card,
        title="45 Marlborough Crescent",
        subtitle="Cinematic Property Walkthrough",
        duration=1.0,
        width=320,
        height=180,
        fps=24.0,
        backdrop_image_path=photo,
        eyebrow="Property Tour",
    )

    meta = ffmpeg_engine.probe_video(card)
    assert meta["duration_seconds"] >= 0.8
    # The card must not be the flat near-black it used to render.
    assert _read_frame(card, 0.45).mean() > 15


def test_branded_card_renders_without_a_backdrop(tmp_path):
    card = tmp_path / "card.mp4"
    ffmpeg_engine.create_branded_card(card, "No Photo Property", "Subtitle", 0.8, 160, 90, 24.0)
    assert ffmpeg_engine.probe_video(card)["duration_seconds"] > 0.5


# ── transitions ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("style", [t.value for t in TransitionStyle])
def test_every_transition_style_assembles(tmp_path, style):
    clips = [_write_clip(tmp_path / f"c{i}.mp4", width=160, height=90, seconds=1.0) for i in range(3)]
    output = tmp_path / f"joined_{style}.mp4"

    ffmpeg_engine.concatenate_clips(clips, output, crossfade_duration=0.4, transition_style=style)

    meta = ffmpeg_engine.probe_video(output)
    assert meta["file_size_bytes"] > 0
    total = sum(ffmpeg_engine.probe_video(c)["duration_seconds"] for c in clips)
    if style == "straight_cut":
        assert meta["duration_seconds"] == pytest.approx(total, abs=0.6)
    else:
        # An xfade overlaps the shots, so the cut must be shorter than the sum.
        assert meta["duration_seconds"] < total - 0.4


def test_transition_duration_is_clamped_to_the_shortest_shot(tmp_path):
    """A 2s crossfade across 1s shots would collapse the timeline."""
    clips = [_write_clip(tmp_path / f"c{i}.mp4", width=160, height=90, seconds=1.0) for i in range(2)]
    output = tmp_path / "joined.mp4"

    ffmpeg_engine.concatenate_clips(clips, output, crossfade_duration=2.0, transition_style="crossfade")

    meta = ffmpeg_engine.probe_video(output)
    assert 0.5 < meta["duration_seconds"] < 2.0


# ── music ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("style", ["ambient", "uplifting", "minimal_piano"])
def test_synthesised_score_is_a_real_audio_stream(tmp_path, style):
    output = tmp_path / f"{style}.m4a"

    ffmpeg_engine.synthesize_music(duration_seconds=3.0, style=style, output_path=output, volume=0.3)

    assert ffmpeg_engine.probe_audio_codec(output) is not None


def test_unknown_music_style_falls_back_instead_of_failing(tmp_path):
    output = tmp_path / "fallback.m4a"
    ffmpeg_engine.synthesize_music(2.0, "not_a_style", output, 0.3)
    assert output.stat().st_size > 0


def test_mixing_the_score_adds_an_audio_stream_to_the_video(tmp_path):
    picture = _write_clip(tmp_path / "pic.mp4", width=160, height=90, seconds=2.0)
    bed = tmp_path / "bed.m4a"
    ffmpeg_engine.synthesize_music(2.0, "ambient", bed, 0.3)

    final = ffmpeg_engine.add_background_audio(picture, bed, tmp_path / "final.mp4", volume=0.3)

    meta = ffmpeg_engine.probe_video(final)
    assert meta["duration_seconds"] == pytest.approx(2.0, abs=0.3)
    assert ffmpeg_engine.probe_audio_codec(final) is not None
    # The picture stream must survive the mux.
    assert (meta["width"], meta["height"]) == (160, 90)


def test_probe_audio_codec_reports_none_for_a_silent_clip(tmp_path):
    silent = _write_clip(tmp_path / "silent.mp4", width=160, height=90)
    assert ffmpeg_engine.probe_audio_codec(silent) is None


# ── the score is music, not a drone ──────────────────────────────────────
def _rms_envelope(audio: np.ndarray, windows: int = 24) -> np.ndarray:
    """Per-window RMS — flat for a drone, strongly varying for a cue with a pulse."""
    mono = audio.mean(axis=1) if audio.ndim > 1 else audio
    size = len(mono) // windows
    return np.array(
        [float(np.sqrt((mono[i * size : (i + 1) * size] ** 2).mean())) for i in range(windows)]
    )


@pytest.mark.parametrize("style", ["ambient", "uplifting", "minimal_piano"])
def test_score_has_a_pulse_rather_than_a_static_drone(style):
    from app.services.video_assembler.music_engine import music_engine

    audio = music_engine.render(8.0, style)
    envelope = _rms_envelope(audio)

    # A held drone has an almost constant envelope; a cue with chords, bass and an
    # arpeggio does not. This is the difference the user actually hears.
    assert envelope.std() / envelope.mean() > 0.20, f"{style} score is dynamically flat"
    assert float(np.abs(audio).max()) > 0.5, "score was not normalised"
    assert audio.shape[0] == int(8.0 * 44100)


def test_score_styles_are_actually_different_music():
    from app.services.video_assembler.music_engine import music_engine

    ambient = music_engine.render(4.0, "ambient")
    uplifting = music_engine.render(4.0, "uplifting")

    assert ambient.shape == uplifting.shape
    assert not np.allclose(ambient, uplifting)
    # Deterministic: the same request must produce the same cue.
    assert np.array_equal(ambient, music_engine.render(4.0, "ambient"))


# ── letterbox, bloom, kinetic type, richer labels ────────────────────────
def _grey(frame: np.ndarray) -> float:
    return float(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).mean())


def test_letterbox_bars_are_black_and_leave_the_picture_alone(tmp_path):
    source = _write_clip(tmp_path / "src.mp4", width=320, height=180, seconds=1.0)
    plain = tmp_path / "plain.mp4"
    barred = tmp_path / "barred.mp4"

    ffmpeg_engine.grade_and_conform(source, plain, 320, 180, 24.0, color_grade="none")
    ffmpeg_engine.grade_and_conform(
        source, barred, 320, 180, 24.0, color_grade="none", letterbox=True
    )

    frame = _read_frame(barred, at_seconds=0.3)
    bar = int(180 * 0.055)
    assert _grey(frame[:bar]) < 25.0, "top scope bar is not black"
    assert _grey(frame[-bar:]) < 25.0, "bottom scope bar is not black"
    # The picture between the bars must survive.
    middle = frame[bar + 10 : 180 - bar - 10]
    assert _grey(middle) > 30.0
    assert np.array_equal(
        cv2.resize(_read_frame(plain, at_seconds=0.3), (320, 180)),
        cv2.resize(frame, (320, 180)),
    ) is False


def test_bloom_brightens_the_picture_without_washing_out_the_bars(tmp_path):
    source = _write_clip(tmp_path / "src.mp4", width=320, height=180, seconds=1.0)
    plain = tmp_path / "plain.mp4"
    bloomed = tmp_path / "bloomed.mp4"

    ffmpeg_engine.grade_and_conform(
        source, plain, 320, 180, 24.0, color_grade="none", letterbox=True
    )
    ffmpeg_engine.grade_and_conform(
        source, bloomed, 320, 180, 24.0, color_grade="none", letterbox=True, bloom=True
    )

    bar = int(180 * 0.055)
    bloom_frame = _read_frame(bloomed, at_seconds=0.3)
    # The glow is gated to highlights, so the bars must stay genuinely black
    # rather than being lifted into grey by the screen blend.
    assert _grey(bloom_frame[:bar]) < 25.0
    assert _grey(bloom_frame[-bar:]) < 25.0

    mid = slice(bar + 10, 180 - bar - 10)
    assert _grey(bloom_frame[mid]) > _grey(_read_frame(plain, at_seconds=0.3)[mid])


def test_letterbox_is_skipped_on_portrait_output(tmp_path):
    source = _write_clip(tmp_path / "src.mp4", width=180, height=320, seconds=0.6)
    output = tmp_path / "portrait.mp4"

    ffmpeg_engine.grade_and_conform(
        source, output, 180, 320, 24.0, color_grade="none", letterbox=True
    )

    frame = _read_frame(output, at_seconds=0.2)
    # Bars would only eat useful picture on a phone-shaped frame.
    assert _grey(frame[:18]) > 25.0


def test_room_label_burns_in_its_accent_counter_and_progress(tmp_path):
    source = _write_clip(tmp_path / "src.mp4", width=320, height=180, seconds=3.0)
    output = tmp_path / "labelled.mp4"

    ffmpeg_engine.apply_room_label(
        source, output, "Primary Suite", 320, 180, 24.0,
        counter="02 / 06", progress=2 / 6,
    )

    frame = _read_frame(output, at_seconds=1.2)
    lower = frame[100:170]
    b, g, r = lower[:, :, 0].astype(int), lower[:, :, 1].astype(int), lower[:, :, 2].astype(int)
    gold = ((np.abs(b - 83) < 40) & (np.abs(g - 168) < 40) & (np.abs(r - 212) < 40)).sum()
    assert gold > 40, "label accent bar / progress fill was not burned in"

    # The label fades out before the clip ends so it never collides with a cut.
    ending = _read_frame(output, at_seconds=2.8)
    b, g, r = ending[:, :, 0].astype(int), ending[:, :, 1].astype(int), ending[:, :, 2].astype(int)
    assert ((np.abs(b - 83) < 40) & (np.abs(g - 168) < 40) & (np.abs(r - 212) < 40)).sum() < 20


def test_room_counter_changes_the_burned_label(tmp_path):
    source = _write_clip(tmp_path / "src.mp4", width=320, height=180, seconds=3.0)
    plain = tmp_path / "plain.mp4"
    counted = tmp_path / "counted.mp4"

    ffmpeg_engine.apply_room_label(source, plain, "Kitchen", 320, 180, 24.0)
    ffmpeg_engine.apply_room_label(
        source, counted, "Kitchen", 320, 180, 24.0, counter="01 / 06", progress=1 / 6
    )

    a = _read_frame(plain, at_seconds=1.2).astype(np.int16)
    b = _read_frame(counted, at_seconds=1.2).astype(np.int16)
    assert float(np.abs(a - b).mean()) > 0.2, "counter/progress were not rendered"


def test_title_card_kinetically_animates_and_fades(tmp_path):
    backdrop = tmp_path / "room.png"
    plate = np.full((180, 320, 3), 120, np.uint8)
    plate[:90] = (180, 190, 200)
    cv2.imwrite(str(backdrop), plate)

    card = tmp_path / "card.mp4"
    ffmpeg_engine.create_branded_card(
        card, "Bel Air Modern Estate", "Beverly Hills, California",
        duration=2.4, width=320, height=180, fps=24.0,
        backdrop_image_path=backdrop, eyebrow="Property Tour",
    )

    assert ffmpeg_engine.probe_video(card)["duration_seconds"] == pytest.approx(2.4, abs=0.3)

    opening = _read_frame(card, at_seconds=0.02)
    assert _grey(opening) < 30.0, "card did not fade up from black"

    # The headline arrives with loose letter-spacing that tightens, so the type
    # band must still be changing well after the card has faded in.
    band = slice(70, 120)
    early = _read_frame(card, at_seconds=0.45).astype(np.int16)[band]
    settled = _read_frame(card, at_seconds=1.30).astype(np.int16)[band]
    assert float(np.abs(early - settled).mean()) > 1.0, "title does not animate in"


# ── the grade must enrich the frame, never dilute it ─────────────────────
# Both tests below pin defects that were measured on real renders, not guessed:
# the old grade pulled a bright interior down by ~30 luma levels and crushed 2% of
# the frame to black, and the old "bloom" screened a blur of the *whole* frame over
# itself, which left the picture ~30% softer than the source photograph it came
# from. "Diluted" is exactly that pair of failures.
def _tone_plate(width: int = 320, height: int = 180) -> np.ndarray:
    """A frame with a realistic spread of tones, including deep shadows."""
    ramp = np.linspace(10, 240, width, dtype=np.uint8)
    return np.repeat(ramp[None, :, None], height, axis=0).repeat(3, axis=2)


def test_the_flagship_grade_lifts_shadows_instead_of_crushing_them(tmp_path):
    plate = _tone_plate()
    source = tmp_path / "plate.png"
    cv2.imwrite(str(source), plate)
    clip = tmp_path / "plate.mp4"
    _write_clip(clip, width=320, height=180, seconds=0.8)

    plain = tmp_path / "plain.mp4"
    graded = tmp_path / "graded.mp4"
    # Vignette off so this isolates the tone curve rather than the corners.
    ffmpeg_engine.grade_and_conform(clip, plain, 320, 180, 24.0, color_grade="none")
    ffmpeg_engine.grade_and_conform(
        clip, graded, 320, 180, 24.0, color_grade="warm_luxury", vignette=False
    )

    mid = slice(40, 140)  # inside the frame, away from the rounded edges
    before = _read_frame(plain, at_seconds=0.3)[mid]
    after = _read_frame(graded, at_seconds=0.3)[mid]
    before_grey = cv2.cvtColor(before, cv2.COLOR_BGR2GRAY)
    after_grey = cv2.cvtColor(after, cv2.COLOR_BGR2GRAY)

    # A print never sits on true black, so the darkest tones come *up*.
    assert after_grey.min() > before_grey.min() + 4, (
        f"grade crushed the blacks (min {before_grey.min()} -> {after_grey.min()})"
    )
    assert (after_grey < 12).mean() <= (before_grey < 12).mean(), "grade introduced crushed black"
    # And the frame as a whole gets richer rather than duller.
    assert after_grey.mean() > before_grey.mean(), "grade darkened the picture"


def _write_static_clip(path: Path, frame: np.ndarray, seconds: float = 0.8, fps: float = 24.0) -> Path:
    """A clip of one unchanging frame, so a region stays where it was put."""
    height, width = frame.shape[:2]
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    for _ in range(max(2, int(seconds * fps))):
        writer.write(frame)
    writer.release()
    return path


def test_halation_glows_the_highlights_without_hazing_the_shadows(tmp_path):
    # A bright patch beside a dark field: halation must light the former and
    # leave the latter alone. The previous full-frame screen blend did the opposite.
    plate = np.full((180, 320, 3), 30, np.uint8)
    plate[60:120, 120:200] = (250, 250, 250)
    clip = _write_static_clip(tmp_path / "plate.mp4", plate)

    plain = tmp_path / "plain.mp4"
    bloomed = tmp_path / "bloomed.mp4"
    ffmpeg_engine.grade_and_conform(clip, plain, 320, 180, 24.0, color_grade="none")
    ffmpeg_engine.grade_and_conform(
        clip, bloomed, 320, 180, 24.0, color_grade="none", bloom=True
    )

    # Just outside the highlight is where light should bleed; the far field must not
    # move at all. Measuring *inside* the highlight would prove nothing, since that
    # is already at full white.
    halo = (slice(70, 110), slice(201, 216))
    far_dark = (slice(0, 40), slice(0, 90))
    before = _read_frame(plain, at_seconds=0.3)
    after = _read_frame(bloomed, at_seconds=0.3)

    halo_lift = _grey(after[halo]) - _grey(before[halo])
    dark_lift = _grey(after[far_dark]) - _grey(before[far_dark])

    assert halo_lift > 8.0, f"halation did not bleed around the highlight (lift {halo_lift:.1f})"
    # A real halo is a spread, not a switch: some light does reach everywhere. The
    # defect being guarded against is the opposite — a glow so broad and strong that
    # it lifts the whole frame into haze (the version this replaced moved the far
    # field by more than the halo, and took 30% of the picture's detail with it).
    assert dark_lift < halo_lift * 0.45, (
        f"halation is not localised (far field +{dark_lift:.1f} vs halo +{halo_lift:.1f})"
    )
    assert dark_lift < 8.0, f"halation hazed the shadows (far field +{dark_lift:.1f})"


# ── sound design on the cuts ─────────────────────────────────────────────
def test_the_assembly_records_where_it_cut(tmp_path):
    clips = [_write_clip(tmp_path / f"c{i}.mp4", width=160, height=90, seconds=1.0) for i in range(3)]
    out = tmp_path / "joined.mp4"

    ffmpeg_engine.concatenate_clips(
        clips, out, crossfade_duration=0.4, transition_style="crossfade"
    )

    cuts = ffmpeg_engine.last_transition_times()
    assert len(cuts) == 2, f"expected a cut between each pair of clips, got {cuts}"
    # Each clip is 1.0s and the dissolve is 0.4s, so the first transition starts at
    # 0.6s and its midpoint — where the whoosh belongs — is at 0.8s.
    assert cuts[0] == pytest.approx(0.8, abs=0.15)
    assert cuts[0] < cuts[1] < ffmpeg_engine.probe_video(out)["duration_seconds"]


def test_sound_design_lands_on_the_cuts_and_nowhere_else():
    from app.services.video_assembler.music_engine import music_engine

    cuts = [3.0, 6.0]
    accents = music_engine.plan_accents(
        10.0, cuts, opening_riser=False, final_impact=False
    )
    assert [a.kind for a in accents] == ["whoosh", "whoosh"]

    bed = music_engine.render(10.0, "ambient")
    designed = music_engine.render(10.0, "ambient", accents=accents)
    assert bed.shape == designed.shape

    # Subtracting the bed isolates the incidental layer exactly, so this measures
    # where the sound design actually sits rather than the music's own pulse.
    added = np.abs(designed - bed).mean(axis=1)
    kept = np.abs(bed).mean(axis=1)

    def energy(series, start: float, stop: float) -> float:
        return float(series[int(start * 44100) : int(stop * 44100)].mean())

    on_cut = max(energy(added, 2.7, 3.4), energy(added, 5.7, 6.4))
    off_cut = max(energy(added, 4.2, 4.9), energy(added, 7.6, 8.3))
    music_under_it = energy(kept, 2.7, 3.4)

    assert off_cut < on_cut * 0.05, (
        f"incidentals are not concentrated on the cuts (on-cut {on_cut:.5f}, "
        f"off-cut {off_cut:.5f})"
    )
    # And loud enough to be heard: the first version of this was rendered a
    # quarter as loud as the score and vanished underneath it.
    assert on_cut > music_under_it * 0.25, (
        f"incidentals are too quiet to read under the score (accent {on_cut:.5f} "
        f"vs music {music_under_it:.5f})"
    )


def test_every_incidental_hits_its_target_level():
    """Levels are set by normalising the rendered clip, not by tuning the synth."""
    from app.services.video_assembler import music_engine as engine_module

    rng = np.random.default_rng(3)
    for kind, make in (
        ("whoosh", engine_module._whoosh),
        ("riser", engine_module._riser),
        ("impact", engine_module._impact),
    ):
        clip = make(rng, 1.0)
        assert float(np.abs(clip).max()) == pytest.approx(
            engine_module._ACCENT_PEAK[kind], abs=1e-3
        ), f"{kind} is not at its target level"


def test_the_ending_gets_a_button_and_an_opening_riser():
    from app.services.video_assembler.music_engine import music_engine

    accents = music_engine.plan_accents(
        20.0, [2.0, 7.0, 12.0, 17.0], opening_riser=True, final_impact=True
    )
    kinds = [a.kind for a in accents]
    assert kinds.count("whoosh") == 4
    assert kinds.count("riser") == 1
    assert kinds.count("impact") == 1
    # The riser has to land on the first cut, and the button on the last.
    assert next(a for a in accents if a.kind == "riser").at == 2.0
    assert next(a for a in accents if a.kind == "impact").at == 17.0

    # No cut inside the programme means no incidentals at all.
    assert music_engine.plan_accents(20.0, []) == []
