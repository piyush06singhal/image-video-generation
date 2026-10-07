"""A tiny procedural composer — real music for the score, with no licensed assets.

The previous score was a stack of sine partials with a slow swell. It was
technically audio and completely static: no pulse, no harmonic movement, no
rhythm, no space. That is why a finished walkthrough still felt like a slideshow
with a hum under it.

This module writes an actual cue instead: a chord progression that moves, a pad to
hold it, a bass on the root, a plucked arpeggio that gives it a pulse, soft
percussion where the style wants it, and a reverb tail so it sits in a room
rather than in a vacuum. Everything is deterministic and generated from numpy —
nothing is downloaded and nothing is licensed.

It is deliberately underscore, not a song: it should make the picture feel
expensive without ever asking for attention. Sized at 44.1kHz stereo, this is
cheap enough to run inline during assembly.
"""

from dataclasses import dataclass
from enum import Enum
import wave
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

SAMPLE_RATE = 44100

# Semitone offsets of the natural notes, used by the tiny pitch-name parser.
_PITCH_CLASS = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def note_to_hz(name: str) -> float:
    """``"A3"`` / ``"C#4"`` / ``"Bb2"`` -> frequency in Hz (A4 = 440)."""
    letter = name[0].upper()
    semitone = _PITCH_CLASS[letter]
    i = 1
    while i < len(name) and name[i] in "#b":
        semitone += 1 if name[i] == "#" else -1
        i += 1
    octave = int(name[i:])
    midi = (octave + 1) * 12 + semitone
    return 440.0 * (2.0 ** ((midi - 69) / 12.0))


def chord_to_hz(notes: Sequence[str]) -> List[float]:
    return [note_to_hz(n) for n in notes]


class Scene(Enum):
    """Mood of the cue, which is what the user actually picks in the studio."""

    AMBIENT = "ambient"
    UPLIFTING = "uplifting"
    MINIMAL_PIANO = "minimal_piano"


# Each chord is (bass note, pad voicing). The progressions are deliberately
# diatonic and loop-friendly, because a property tour is watched once and must
# never land on a sour chord.
_PROGRESSIONS: Dict[str, List[Tuple[str, List[str]]]] = {
    # Am - F - C - G: wistful, filmic, and the safest bed for luxury interiors.
    "ambient": [
        ("A2", ["A3", "C4", "E4", "E4"]),
        ("F2", ["F3", "A3", "C4", "C4"]),
        ("C3", ["C4", "E4", "G4", "G4"]),
        ("G2", ["G3", "B3", "D4", "D4"]),
    ],
    # C - G - Am - F: brighter and more forward, for a reel that has to sell.
    "uplifting": [
        ("C3", ["C4", "E4", "G4"]),
        ("G2", ["G3", "B3", "D4"]),
        ("A2", ["A3", "C4", "E4"]),
        ("F2", ["F3", "A3", "C4"]),
    ],
    # Sparse and close-voiced, played as a plucked figure rather than a pad.
    "minimal_piano": [
        ("A2", ["A3", "E4", "C5"]),
        ("F2", ["F3", "C4", "A4"]),
        ("C3", ["C4", "G4", "E5"]),
        ("G2", ["G3", "D4", "B4"]),
    ],
}

_TEMPO_BPM = {"ambient": 72, "uplifting": 104, "minimal_piano": 66}

# How much of each element to use, per mood. Turning an element off entirely is
# what separates a "score" from a "drone", so the mix varies by style.
_MIX = {
    "ambient": dict(pad=1.00, bass=0.55, arp=0.42, kick=0.00, hat=0.10, reverb=0.30, arp_div=2.0),
    "uplifting": dict(pad=0.72, bass=0.70, arp=0.62, kick=0.42, hat=0.26, reverb=0.22, arp_div=0.5),
    "minimal_piano": dict(pad=0.34, bass=0.46, arp=1.00, kick=0.00, hat=0.00, reverb=0.34, arp_div=1.0),
}


# ── primitive voices ──────────────────────────────────────────────────────
def _envelope(n: int, attack: float, release: float) -> np.ndarray:
    """Raised-cosine attack/release over ``n`` samples, with a flat sustain."""
    env = np.ones(n, dtype=np.float32)
    a = min(int(attack * SAMPLE_RATE), n // 2)
    r = min(int(release * SAMPLE_RATE), n - a)
    if a > 1:
        env[:a] = 0.5 - 0.5 * np.cos(np.linspace(0.0, np.pi, a, dtype=np.float32))
    if r > 1:
        env[n - r :] *= 0.5 + 0.5 * np.cos(np.linspace(0.0, np.pi, r, dtype=np.float32))
    return env


def _pad_wave(t: np.ndarray, freq: float, detune: float = 0.0) -> np.ndarray:
    """A warm organ-ish tone: a few harmonics with a 1/n-ish rolloff."""
    f = freq * (1.0 + detune)
    out = np.sin(2 * np.pi * f * t)
    for harmonic, gain in ((2, 0.42), (3, 0.20), (4, 0.09)):
        out += gain * np.sin(2 * np.pi * f * harmonic * t)
    return out * (1.0 / 1.71)


def _pluck_wave(t: np.ndarray, freq: float, decay: float) -> np.ndarray:
    """A struck/plucked tone: fast attack, exponential decay, bright onset."""
    env = np.exp(-decay * t) * (1.0 - np.exp(-t * 900.0))
    out = np.sin(2 * np.pi * freq * t)
    for harmonic, gain in ((2, 0.34), (3, 0.15), (5, 0.07)):
        out += gain * np.sin(2 * np.pi * freq * harmonic * t)
    return out * env * (1.0 / 1.56)


def _bass_wave(t: np.ndarray, freq: float) -> np.ndarray:
    """Sine bass with a touch of second harmonic so it reads on small speakers."""
    return (np.sin(2 * np.pi * freq * t) + 0.22 * np.sin(4 * np.pi * freq * t)) * 0.82


# ── delay-line effects (Schroeder reverb) ─────────────────────────────────
def _comb(x: np.ndarray, delay: int, feedback: float) -> np.ndarray:
    """Feedback comb, computed exactly by iterating one delay-period at a time.

    A per-sample Python loop over a ~1M-sample buffer would be far too slow, but
    y[i] only ever depends on y[i - delay], so whole delay-periods can be advanced
    vectorised in one step.
    """
    y = x.astype(np.float32).copy()
    n = len(y)
    for start in range(delay, n, delay):
        end = min(start + delay, n)
        y[start:end] += feedback * y[start - delay : end - delay]
    return y


def _allpass(x: np.ndarray, delay: int, gain: float) -> np.ndarray:
    """Schroeder allpass, used to smear the comb output into a diffuse tail."""
    n = len(x)
    src = np.concatenate([np.zeros(delay, dtype=np.float32), x.astype(np.float32)])
    y = np.zeros_like(src)
    for start in range(delay, len(src), delay):
        end = min(start + delay, len(src))
        y[start:end] = -gain * src[start:end] + src[start - delay : end - delay] + gain * y[
            start - delay : end - delay
        ]
    return y[delay:n + delay]


def _reverb(x: np.ndarray, mix: float) -> np.ndarray:
    """A small, warm room. Four combs in parallel, two allpasses in series."""
    wet = np.zeros_like(x)
    # Delay times chosen to be mutually prime so the tail does not ring on a pitch.
    for seconds, feedback in ((0.0297, 0.780), (0.0371, 0.806), (0.0411, 0.766), (0.0437, 0.748)):
        wet += _comb(x, int(seconds * SAMPLE_RATE), feedback)
    wet /= 4.0
    for seconds, gain in ((0.0050, 0.70), (0.0017, 0.70)):
        wet = _allpass(wet, int(seconds * SAMPLE_RATE), gain)
    return (1.0 - mix) * x + mix * wet * 0.9


# ── percussion ────────────────────────────────────────────────────────────
def _kick(n: int, strength: float = 1.0) -> np.ndarray:
    t = np.arange(n, dtype=np.float32) / SAMPLE_RATE
    # Pitch sweep 120 Hz -> 46 Hz gives the thump; the click sells the transient.
    freq = 46.0 + 74.0 * np.exp(-t / 0.030)
    phase = 2 * np.pi * np.cumsum(freq) / SAMPLE_RATE
    body = np.sin(phase) * np.exp(-t / 0.150)
    click = np.sin(2 * np.pi * 1800.0 * t) * np.exp(-t / 0.006) * 0.20
    return (body + click) * strength * 0.9


def _hat(n: int, rng: np.random.Generator, strength: float = 1.0) -> np.ndarray:
    t = np.arange(n, dtype=np.float32) / SAMPLE_RATE
    noise = rng.standard_normal(n).astype(np.float32)
    # Crude one-pole high-pass: adjacent-sample difference, twice.
    noise = np.diff(noise, prepend=0.0)
    noise = np.diff(noise, prepend=0.0)
    return noise * np.exp(-t / 0.026) * strength * 0.32


# ── sound design ──────────────────────────────────────────────────────────
# Music alone does not make a cut feel produced; *incidentals* do. A picture edit
# normally carries a whoosh on every transition, a riser into the first shot and a
# low button as the end card arrives. Without them a tour reads as a slideshow with
# a bed under it, which is precisely the complaint these sounds exist to fix. They
# are synthesised from the same numpy primitives as the score, so nothing is
# licensed and nothing is downloaded.
@dataclass(frozen=True)
class Accent:
    """One incidental, positioned at the instant it should *land*."""

    kind: str  # "whoosh" | "riser" | "impact"
    at: float
    gain: float = 1.0


# Target peak per kind. These are applied *after* shaping, by normalising each
# rendered incidental, because the synth chain attenuates unpredictably: the
# whoosh's band-pass leaves it at a quarter of its nominal level, which made the
# first version of this sound design inaudible under a bed peaking at 0.92.
# Setting the level in one place means changing the filter sweep can never
# silently change how loud the cut sounds.
_ACCENT_PEAK = {"whoosh": 0.55, "riser": 0.50, "impact": 0.70}


def _finish(data: np.ndarray, kind: str, gain: float) -> np.ndarray:
    """Normalises an incidental to its target peak, then applies the caller's gain."""
    peak = float(np.max(np.abs(data))) or 1.0
    return (data * (_ACCENT_PEAK[kind] * gain / peak)).astype(np.float32)


def _sweep_noise(
    n: int,
    rng: np.random.Generator,
    f_lo: float,
    f_hi: float,
    q_oct: float = 0.8,
    block: int = 512,
) -> np.ndarray:
    """Overlap-add band-passed noise whose centre frequency sweeps ``f_lo -> f_hi``.

    Each block gets its own Gaussian band mask in the frequency domain, so the
    sweep is a genuine filter movement rather than an amplitude trick. Hann
    windows at 50% overlap sum to unity, so the plain overlap-add is
    gain-correct without needing a second synthesis window.
    """
    hop = block // 2
    source = rng.standard_normal(n + block).astype(np.float32)
    window = np.hanning(block).astype(np.float32)
    freqs = np.maximum(np.fft.rfftfreq(block, 1.0 / SAMPLE_RATE), 1.0)
    acc = np.zeros(n + block, dtype=np.float32)
    for pos in range(0, n, hop):
        segment = source[pos : pos + block] * window
        spectrum = np.fft.rfft(segment)
        frac = pos / max(1, n - 1)
        centre = f_lo * (f_hi / f_lo) ** frac
        band = np.exp(-0.5 * (np.log2(freqs / centre) / q_oct) ** 2)
        acc[pos : pos + block] += np.fft.irfft(spectrum * band, block).astype(np.float32)
    return acc[:n]


def _whoosh(rng: np.random.Generator, gain: float) -> np.ndarray:
    """A short filtered-noise swish: the sound of air moving with the cut."""
    n = int(0.85 * SAMPLE_RATE)
    t = np.arange(n, dtype=np.float32) / SAMPLE_RATE
    body = _sweep_noise(n, rng, 220.0, 5200.0, q_oct=0.72)
    rise = np.clip(t / 0.30, 0.0, 1.0) ** 1.4
    fall = np.exp(-np.clip(t - 0.30, 0.0, None) / 0.22)
    body = body * (rise * fall)
    air = np.diff(rng.standard_normal(n).astype(np.float32), prepend=0.0)
    air *= np.exp(-np.clip(t - 0.22, 0.0, None) / 0.18) * 0.10
    mono = (body * 0.9 + air).astype(np.float32)
    # A few ms of delay on one side gives the swish a direction and a width.
    shift = int(0.004 * SAMPLE_RATE)
    right = np.concatenate([np.zeros(shift, dtype=np.float32), mono[:-shift]])
    return _finish(np.stack([mono, right], axis=1), "whoosh", gain)


def _riser(rng: np.random.Generator, gain: float) -> np.ndarray:
    """A build-up that *ends* on the cut, launching the first real shot."""
    n = int(1.7 * SAMPLE_RATE)
    t = np.arange(n, dtype=np.float32) / SAMPLE_RATE
    noise = _sweep_noise(n, rng, 300.0, 3200.0, q_oct=0.6)
    env = (t / t[-1]) ** 2.4
    tail = max(1, int(0.05 * SAMPLE_RATE))
    env[-tail:] *= np.linspace(1.0, 0.0, tail, dtype=np.float32)
    # A low tone climbing an octave over the build adds tension under the noise.
    freq = 110.0 * (2.0 ** (t / t[-1]))
    phase = 2 * np.pi * np.cumsum(freq) / SAMPLE_RATE
    mono = (noise * env * 0.9 + np.sin(phase) * env * 0.22).astype(np.float32)
    return _finish(np.stack([mono, mono], axis=1), "riser", gain)


def _impact(rng: np.random.Generator, gain: float) -> np.ndarray:
    """A soft low button for the end card: warm and final, not a trailer hit."""
    n = int(1.5 * SAMPLE_RATE)
    t = np.arange(n, dtype=np.float32) / SAMPLE_RATE
    freq = 44.0 + 40.0 * np.exp(-t / 0.05)
    phase = 2 * np.pi * np.cumsum(freq) / SAMPLE_RATE
    body = np.sin(phase) * np.exp(-t / 0.42)
    click = np.diff(rng.standard_normal(n).astype(np.float32), prepend=0.0)
    click *= np.exp(-t / 0.018) * 0.30
    mono = (body * 0.8 + click).astype(np.float32)
    # Slightly louder on the right than the left, so it decays into the room.
    return _finish(np.stack([mono, mono * 1.06], axis=1), "impact", gain)


def plan_accents(
    duration_seconds: float,
    cut_times: Sequence[float],
    *,
    opening_riser: bool = True,
    final_impact: bool = False,
) -> List[Accent]:
    """Turns the assembly's cut positions into a list of incidentals.

    A whoosh lands on every cut. The riser is only right when a title card precedes
    the first cut (otherwise it would build up to nothing), and the closing button
    only when an end card follows the last one.
    """
    duration = max(1.0, float(duration_seconds))
    cuts = [float(c) for c in cut_times if 0.4 < float(c) < duration - 0.1]
    if not cuts:
        return []
    accents = [Accent("whoosh", c) for c in cuts]
    if opening_riser:
        accents.append(Accent("riser", cuts[0], gain=0.95))
    if final_impact:
        accents.append(Accent("impact", cuts[-1], gain=0.9))
    return accents


def _mix_accents(stereo: np.ndarray, accents: Sequence[Accent]) -> np.ndarray:
    """Adds incidentals on top of the finished bed, then keeps the sum in range."""
    out = stereo.copy()
    n = len(out)
    for index, accent in enumerate(accents):
        rng = np.random.default_rng(700_000 + index * 131 + int(round(accent.at * 1000)))
        if accent.kind == "whoosh":
            clip = _whoosh(rng, accent.gain)
            onset = accent.at - 0.26  # its peak is 0.26s in; land the peak on the cut
        elif accent.kind == "riser":
            clip = _riser(rng, accent.gain)
            onset = accent.at - len(clip) / SAMPLE_RATE  # it ends on the cut
        elif accent.kind == "impact":
            clip = _impact(rng, accent.gain)
            onset = accent.at
        else:
            continue

        start = int(round(onset * SAMPLE_RATE))
        src_lo = max(0, -start)
        dst = max(0, start)
        count = min(len(clip) - src_lo, n - dst)
        if count <= 0:
            continue
        out[dst : dst + count] += clip[src_lo : src_lo + count]

    peak = float(np.max(np.abs(out))) or 1.0
    if peak > 0.99:
        # Duck the whole bed rather than clip or distort it. Loudness is
        # normalised downstream, so a dB or two of headroom costs nothing.
        out *= 0.99 / peak
    return out.astype(np.float32)


# ── arrangement ───────────────────────────────────────────────────────────
class MusicEngine:
    """Renders a looping progression long enough to cover an arbitrary runtime."""

    def render(
        self,
        duration_seconds: float,
        style: str,
        accents: Sequence[Accent] = (),
    ) -> np.ndarray:
        """Returns float32 stereo audio shaped ``(n_samples, 2)`` in ``[-1, 1]``.

        ``accents`` are mixed *after* the bed's fades, so a closing button that
        lands during the outro fade-out is still heard.
        """
        name = style if style in _PROGRESSIONS else Scene.AMBIENT.value
        duration = max(1.0, float(duration_seconds))
        n = int(round(duration * SAMPLE_RATE))

        bpm = _TEMPO_BPM[name]
        mix = _MIX[name]
        beats_per_bar = 4
        beat = 60.0 / bpm
        bar = beat * beats_per_bar
        progression = _PROGRESSIONS[name]

        left = np.zeros(n, dtype=np.float32)
        right = np.zeros(n, dtype=np.float32)
        rng = np.random.default_rng(20261006)  # deterministic renders

        # ── harmonic bed: pad + bass, one chord per bar, looped to fill ──
        n_bars = int(np.ceil(duration / bar)) + 1
        for bar_index in range(n_bars):
            start = int(round(bar_index * bar * SAMPLE_RATE))
            if start >= n:
                break
            length = int(round(bar * SAMPLE_RATE))
            count = min(length, n - start)
            bass_note, voicing = progression[bar_index % len(progression)]
            t = np.arange(length, dtype=np.float32) / SAMPLE_RATE

            # Release is long enough to overlap the next chord, so the harmony
            # crossfades instead of cutting.
            pad_env = _envelope(length, attack=0.9, release=1.4)
            if mix["pad"] > 0.0:
                for idx, note in enumerate(chord_to_hz(voicing)):
                    detune = -0.0016 if idx % 2 == 0 else 0.0016
                    tone = _pad_wave(t, note, detune) * pad_env * mix["pad"]
                    # High notes lean slightly to one side: width without chorus.
                    pan = -0.22 if idx % 2 == 0 else 0.22
                    left[start : start + count] += tone[:count] * (1.0 - pan) * 0.5
                    right[start : start + count] += tone[:count] * (1.0 + pan) * 0.5

            if mix["bass"] > 0.0:
                bass_env = _envelope(length, attack=0.06, release=0.9)
                bass = _bass_wave(t, note_to_hz(bass_note)) * bass_env * mix["bass"]
                left[start : start + count] += bass[:count] * 0.5
                right[start : start + count] += bass[:count] * 0.5

            # ── arpeggio: this is what gives the cue a pulse ──
            if mix["arp"] > 0.0:
                step = beat * mix["arp_div"]
                steps = max(1, int(round(bar / step)))
                tones = chord_to_hz(voicing)
                for s in range(steps):
                    at = int(round((bar_index * bar + s * step) * SAMPLE_RATE))
                    if at >= n:
                        break
                    # Up-and-down figure so the line moves instead of circling.
                    cycle = list(range(len(tones))) + list(range(len(tones) - 2, 0, -1))
                    note = tones[cycle[s % len(cycle)]]
                    # Later steps are quieter, and the downbeats are accented.
                    accent = 1.0 if s % 4 == 0 else 0.62
                    tail = int(round(min(1.6, duration) * SAMPLE_RATE))
                    cnt = min(tail, n - at)
                    lt = np.arange(cnt, dtype=np.float32) / SAMPLE_RATE
                    pluck = _pluck_wave(lt, note, decay=3.4) * mix["arp"] * accent
                    pan = 0.18 if s % 2 == 0 else -0.18
                    left[at : at + cnt] += pluck * (1.0 - pan) * 0.42
                    right[at : at + cnt] += pluck * (1.0 + pan) * 0.42

        # ── percussion: a steady grid far enough under the mix to feel, not hear ──
        if mix["kick"] > 0.0 or mix["hat"] > 0.0:
            total_beats = int(np.ceil(duration / beat)) + 1
            for b in range(total_beats):
                at = int(round(b * beat * SAMPLE_RATE))
                if at >= n:
                    break
                if mix["kick"] > 0.0 and b % 4 in (0, 2):
                    cnt = min(int(0.32 * SAMPLE_RATE), n - at)
                    k = _kick(cnt, mix["kick"])
                    left[at : at + cnt] += k * 0.5
                    right[at : at + cnt] += k * 0.5
                if mix["hat"] > 0.0:
                    cnt = min(int(0.09 * SAMPLE_RATE), n - at)
                    h = _hat(cnt, rng, mix["hat"] * (1.0 if b % 2 else 0.6))
                    left[at : at + cnt] += h * 0.6
                    right[at : at + cnt] += h * 0.4

        # ── space, glue, and a clean ending ──
        left = _reverb(left, mix["reverb"])
        right = _reverb(right, mix["reverb"])

        stereo = np.stack([left, right], axis=1)
        stereo -= stereo.mean(axis=0, keepdims=True)  # remove any DC offset

        # Fades here (not in FFmpeg) so the curve is exact and the cue never
        # starts or stops on a click.
        fade_in = min(1.5, duration * 0.25)
        fade_out = min(2.5, duration * 0.35)
        a = int(fade_in * SAMPLE_RATE)
        r = int(fade_out * SAMPLE_RATE)
        if a > 1:
            stereo[:a] *= np.linspace(0.0, 1.0, a, dtype=np.float32)[:, None]
        if r > 1:
            stereo[-r:] *= np.linspace(1.0, 0.0, r, dtype=np.float32)[:, None]

        peak = float(np.max(np.abs(stereo))) or 1.0
        stereo = (stereo / peak * 0.92).astype(np.float32)

        if accents:
            stereo = _mix_accents(stereo, accents)
        return stereo

    def plan_accents(
        self,
        duration_seconds: float,
        cut_times: Sequence[float],
        *,
        opening_riser: bool = True,
        final_impact: bool = False,
    ) -> List[Accent]:
        """Exposed on the engine so callers hold one object, not two."""
        return plan_accents(
            duration_seconds,
            cut_times,
            opening_riser=opening_riser,
            final_impact=final_impact,
        )

    def write_wav(self, audio: np.ndarray, output_path) -> None:
        """Writes 16-bit PCM so FFmpeg can transcode it to AAC."""
        pcm = np.clip(audio, -1.0, 1.0)
        pcm = (pcm * 32767.0).astype("<i2")
        with wave.open(str(output_path), "wb") as handle:
            handle.setnchannels(2)
            handle.setsampwidth(2)
            handle.setframerate(SAMPLE_RATE)
            handle.writeframes(pcm.tobytes())


music_engine = MusicEngine()
