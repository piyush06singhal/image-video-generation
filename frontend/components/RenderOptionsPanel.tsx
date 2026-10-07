"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import {
  ASPECT_LABELS,
  AspectRatio,
  ColorGrade,
  GRADE_LABELS,
  GRADE_SWATCHES,
  MOTION_LABELS,
  MUSIC_LABELS,
  MotionIntensity,
  MusicStyle,
  REALISM_LABELS,
  RenderOptions,
  RenderPresetInfo,
  TRANSITION_LABELS,
  TransitionStyle,
  targetDimensions,
  optionsAffectClips,
} from "@/types/render-options";
import {
  AlertTriangle,
  Boxes,
  Check,
  Clapperboard,
  Clock,
  Film,
  Loader2,
  Music2,
  Palette,
  Save,
  Settings2,
  Sparkles,
  Tag,
  Volume2,
} from "lucide-react";

interface RenderOptionsPanelProps {
  projectId: string;
  /**
   * Called after a successful save. `clipsAffected` is true when the change
   * reshapes the clips themselves, so the parent can prompt for regeneration.
   */
  onSaved?: (options: RenderOptions, clipsAffected: boolean) => void;
  /** Start expanded (used right before generating clips). */
  defaultOpen?: boolean;
  /** Show the "generate with these settings" call to action. */
  primaryAction?: { label: string; onClick: () => void; disabled?: boolean };
}

function Segmented<T extends string>({
  value,
  options,
  onChange,
}: {
  value: T;
  options: { value: T; label: string }[];
  onChange: (v: T) => void;
}) {
  return (
    <div className="inline-flex flex-wrap gap-1 p-1 rounded-xl bg-[var(--bg-0)] border border-[var(--border-1)]">
      {options.map((opt) => (
        <button
          key={opt.value}
          type="button"
          onClick={() => onChange(opt.value)}
          className={`px-3 py-1.5 rounded-lg text-[11px] font-semibold transition-all ${
            value === opt.value
              ? "bg-[var(--gold-1)] text-white shadow-sm"
              : "text-[var(--text-2)] hover:text-[var(--text-1)]"
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}

function Toggle({
  checked,
  onChange,
  label,
  hint,
  icon,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  label: string;
  hint?: string;
  icon?: React.ReactNode;
}) {
  return (
    <label className="flex items-start gap-3 p-3 rounded-xl bg-[var(--bg-0)] border border-[var(--border-1)] cursor-pointer hover:border-[var(--border-2)] transition-colors">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="mt-0.5 rounded border-[var(--border-2)] text-[var(--gold-1)] focus:ring-[var(--gold-1)]"
      />
      <div className="min-w-0">
        <p className="text-xs font-semibold text-[var(--text-1)] flex items-center gap-1.5">
          {icon}
          {label}
        </p>
        {hint && <p className="text-[11px] text-[var(--text-3)] mt-0.5 leading-relaxed">{hint}</p>}
      </div>
    </label>
  );
}

function Slider({
  label,
  value,
  min,
  max,
  step,
  suffix,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  suffix: string;
  onChange: (v: number) => void;
}) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-semibold text-[var(--text-2)]">{label}</span>
        <span className="text-[11px] font-mono font-bold text-[var(--gold-2)]">
          {value.toFixed(step < 1 ? 1 : 0)}
          {suffix}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="w-full h-1.5 bg-[var(--bg-0)] rounded-lg appearance-none cursor-pointer accent-[var(--gold-1)] border border-[var(--border-1)]"
      />
    </div>
  );
}

export function RenderOptionsPanel({
  projectId,
  onSaved,
  defaultOpen = false,
  primaryAction,
}: RenderOptionsPanelProps) {
  const [open, setOpen] = useState(defaultOpen);
  const [saved, setSaved] = useState<RenderOptions | null>(null);
  const [draft, setDraft] = useState<RenderOptions | null>(null);
  const [presets, setPresets] = useState<RenderPresetInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedFlash, setSavedFlash] = useState(false);

  const load = useCallback(async () => {
    try {
      const [options, presetList] = await Promise.all([
        api.getRenderOptions(projectId),
        api.getRenderPresets().catch(() => [] as RenderPresetInfo[]),
      ]);
      setSaved(options);
      setDraft(options);
      setPresets(presetList);
      setError(null);
    } catch (err) {
      setError((err as { message?: string }).message || "Failed to load render settings.");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    void load();
  }, [load]);

  const dirty = useMemo(() => {
    if (!saved || !draft) return false;
    return JSON.stringify(saved) !== JSON.stringify(draft);
  }, [saved, draft]);

  const clipsAffected = useMemo(
    () => (saved && draft ? optionsAffectClips(saved, draft) : false),
    [saved, draft]
  );

  const patch = (fields: Partial<RenderOptions>) =>
    setDraft((prev) => (prev ? { ...prev, ...fields } : prev));

  const handleSave = async () => {
    if (!draft) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await api.updateRenderOptions(projectId, {
        options: draft,
        replace: true,
      });
      setSaved(updated);
      setDraft(updated);
      setSavedFlash(true);
      window.setTimeout(() => setSavedFlash(false), 2200);
      onSaved?.(updated, clipsAffected);
    } catch (err) {
      setError((err as { message?: string }).message || "Failed to save render settings.");
    } finally {
      setSaving(false);
    }
  };

  const applyPreset = (preset: RenderPresetInfo) => {
    // Presets are applied on the backend so the preset's canonical values (and
    // anything the client does not know about) are authoritative.
    setSaving(true);
    setError(null);
    void api
      .updateRenderOptions(projectId, { preset: preset.id })
      .then((updated) => {
        setSaved(updated);
        setDraft(updated);
        onSaved?.(updated, true);
      })
      .catch((err: { message?: string }) =>
        setError(err.message || "Failed to apply preset.")
      )
      .finally(() => setSaving(false));
  };

  const estimate = useMemo(() => {
    if (!draft) return null;
    const [w, h] = targetDimensions(draft.aspect_ratio, draft.resolution);
    const seconds =
      draft.scene_duration_seconds +
      (draft.intro_title_enabled ? draft.intro_duration_seconds : 0) +
      (draft.outro_enabled ? draft.outro_duration_seconds : 0);
    return { w, h, seconds };
  }, [draft]);

  if (loading) {
    return (
      <div className="glass rounded-2xl p-5 border border-[var(--border-2)] flex items-center gap-3">
        <Loader2 className="w-4 h-4 animate-spin text-[var(--gold-1)]" />
        <span className="text-xs text-[var(--text-2)]">Loading cinematic settings…</span>
      </div>
    );
  }

  if (!draft || !saved) {
    return (
      <div className="glass rounded-2xl p-5 border border-red-500/30 text-xs text-red-300">
        {error || "Render settings are unavailable."}
      </div>
    );
  }

  const activePresetId = presets.find((p) => p.id === draft.preset)?.id ?? draft.preset;

  return (
    <div className="glass rounded-2xl border border-[var(--border-2)] overflow-hidden">
      {/* Header */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between gap-4 p-5 text-left hover:bg-[var(--bg-0)]/40 transition-colors"
      >
        <div className="flex items-center gap-3 min-w-0">
          <Clapperboard className="w-5 h-5 text-[var(--gold-1)] shrink-0" />
          <div className="min-w-0">
            <p className="text-sm font-bold text-[var(--text-1)] flex items-center gap-2">
              Cinematic Settings
              {dirty && (
                <span className="badge badge-gold text-[9px] font-bold uppercase">Unsaved</span>
              )}
              {!dirty && savedFlash && (
                <span className="badge badge-success text-[9px] font-bold uppercase flex items-center gap-1">
                  <Check size={10} /> Saved
                </span>
              )}
            </p>
            <p className="text-[11px] text-[var(--text-3)] mt-0.5 truncate">
              {presets.find((p) => p.id === activePresetId)?.label ?? draft.preset} ·{" "}
              {draft.aspect_ratio} {draft.resolution} · {draft.fps}fps ·{" "}
              {draft.scene_duration_seconds}s per room
              {draft.music_enabled ? ` · ${MUSIC_LABELS[draft.music_style]} score` : " · silent"}
            </p>
          </div>
        </div>
        <Settings2
          className={`w-4 h-4 text-[var(--text-3)] shrink-0 transition-transform ${
            open ? "rotate-90" : ""
          }`}
        />
      </button>

      {open && (
        <div className="px-5 pb-5 space-y-6 border-t border-[var(--border-1)] pt-5">
          {error && (
            <div className="p-3 bg-red-950/40 border border-red-500/30 rounded-xl text-[11px] text-red-300 flex items-start gap-2">
              <AlertTriangle size={13} className="mt-0.5 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Presets */}
          <div className="space-y-2">
            <p className="text-[11px] font-bold uppercase tracking-wider text-[var(--text-3)] flex items-center gap-1.5">
              <Sparkles size={12} className="text-[var(--gold-1)]" /> Style Presets
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
              {presets.map((preset) => {
                const active = preset.id === activePresetId;
                return (
                  <button
                    key={preset.id}
                    type="button"
                    onClick={() => applyPreset(preset)}
                    disabled={saving}
                    className={`text-left p-3 rounded-xl border transition-all disabled:opacity-60 ${
                      active
                        ? "border-[var(--gold-1)] bg-[var(--gold-dim)]/20 shadow-sm"
                        : "border-[var(--border-1)] bg-[var(--bg-0)] hover:border-[var(--border-2)]"
                    }`}
                  >
                    <p className="text-xs font-bold text-[var(--text-1)] flex items-center gap-1.5">
                      {preset.label}
                      {preset.recommended && (
                        <Tag size={10} className="text-[var(--gold-1)]" />
                      )}
                      {active && <Check size={12} className="text-[var(--gold-1)] ml-auto" />}
                    </p>
                    <p className="text-[10px] text-[var(--text-3)] mt-1 leading-relaxed">
                      {preset.description}
                    </p>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Output format */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            <div className="space-y-3">
              <p className="text-[11px] font-bold uppercase tracking-wider text-[var(--text-3)] flex items-center gap-1.5">
                <Film size={12} className="text-[var(--gold-1)]" /> Frame & Frame Rate
              </p>
              <div className="space-y-2.5">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-[11px] font-semibold text-[var(--text-2)]">Aspect</span>
                  <Segmented<AspectRatio>
                    value={draft.aspect_ratio}
                    onChange={(v) => patch({ aspect_ratio: v })}
                    options={(Object.keys(ASPECT_LABELS) as AspectRatio[]).map((k) => ({
                      value: k,
                      label: ASPECT_LABELS[k],
                    }))}
                  />
                </div>
                <div className="flex items-center justify-between gap-3">
                  <span className="text-[11px] font-semibold text-[var(--text-2)]">Quality</span>
                  <Segmented
                    value={draft.resolution}
                    onChange={(v) => patch({ resolution: v })}
                    options={[
                      { value: "720p" as const, label: "720p" },
                      { value: "1080p" as const, label: "1080p" },
                      { value: "1440p" as const, label: "1440p" },
                    ]}
                  />
                </div>
                <div className="flex items-center justify-between gap-3">
                  <span className="text-[11px] font-semibold text-[var(--text-2)]">FPS</span>
                  <Segmented
                    value={String(draft.fps) as "24" | "30" | "60"}
                    onChange={(v) => patch({ fps: parseInt(v, 10) })}
                    options={[
                      { value: "24" as const, label: "24" },
                      { value: "30" as const, label: "30" },
                      { value: "60" as const, label: "60" },
                    ]}
                  />
                </div>
              </div>
            </div>

            <div className="space-y-3">
              <p className="text-[11px] font-bold uppercase tracking-wider text-[var(--text-3)] flex items-center gap-1.5">
                <Clock size={12} className="text-[var(--gold-1)]" /> Pacing & Motion
              </p>
              <Slider
                label="Seconds per room"
                value={draft.scene_duration_seconds}
                min={2}
                max={12}
                step={0.5}
                suffix="s"
                onChange={(v) => patch({ scene_duration_seconds: v })}
              />
              <div className="flex items-center justify-between gap-3">
                <span className="text-[11px] font-semibold text-[var(--text-2)]">Movement</span>
                <Segmented<MotionIntensity>
                  value={draft.motion_intensity}
                  onChange={(v) => patch({ motion_intensity: v })}
                  options={(Object.keys(MOTION_LABELS) as MotionIntensity[]).map((k) => ({
                    value: k,
                    label: MOTION_LABELS[k],
                  }))}
                />
              </div>
            </div>
          </div>

          {/* Depth & realism — what separates a production from a slideshow */}
          <div className="space-y-3">
            <p className="text-[11px] font-bold uppercase tracking-wider text-[var(--text-3)] flex items-center gap-1.5">
              <Boxes size={12} className="text-[var(--gold-1)]" /> Depth & Realism
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              <Toggle
                checked={draft.depth_parallax}
                onChange={(v) => patch({ depth_parallax: v })}
                label={REALISM_LABELS.depth_parallax.label}
                hint={REALISM_LABELS.depth_parallax.hint}
              />
              <Toggle
                checked={draft.motion_blur}
                onChange={(v) => patch({ motion_blur: v })}
                label={REALISM_LABELS.motion_blur.label}
                hint={REALISM_LABELS.motion_blur.hint}
              />
            </div>
            {!draft.depth_parallax && (
              <p className="text-[10px] text-[var(--text-3)] leading-relaxed">
                Without depth the camera still moves, but every object in the frame
                travels together — which is the look that reads as a panning photo.
              </p>
            )}
          </div>

          {/* Transitions */}
          <div className="space-y-3">
            <p className="text-[11px] font-bold uppercase tracking-wider text-[var(--text-3)] flex items-center gap-1.5">
              <Clapperboard size={12} className="text-[var(--gold-1)]" /> Transitions
            </p>
            <Segmented<TransitionStyle>
              value={draft.transition_style}
              onChange={(v) => patch({ transition_style: v })}
              options={(Object.keys(TRANSITION_LABELS) as TransitionStyle[]).map((k) => ({
                value: k,
                label: TRANSITION_LABELS[k],
              }))}
            />
            {draft.transition_style !== "straight_cut" && (
              <Slider
                label="Transition length"
                value={draft.transition_duration_seconds}
                min={0.2}
                max={2}
                step={0.1}
                suffix="s"
                onChange={(v) => patch({ transition_duration_seconds: v })}
              />
            )}
          </div>

          {/* Look */}
          <div className="space-y-3">
            <p className="text-[11px] font-bold uppercase tracking-wider text-[var(--text-3)] flex items-center gap-1.5">
              <Palette size={12} className="text-[var(--gold-1)]" /> Look
            </p>
            <div className="flex flex-wrap gap-2">
              {(Object.keys(GRADE_LABELS) as ColorGrade[]).map((grade) => (
                <button
                  key={grade}
                  type="button"
                  onClick={() => patch({ color_grade: grade })}
                  className={`flex items-center gap-2 pl-1.5 pr-3 py-1.5 rounded-xl border text-[11px] font-semibold transition-all ${
                    draft.color_grade === grade
                      ? "border-[var(--gold-1)] bg-[var(--gold-dim)]/20 text-[var(--text-1)]"
                      : "border-[var(--border-1)] bg-[var(--bg-0)] text-[var(--text-2)] hover:border-[var(--border-2)]"
                  }`}
                >
                  <span
                    className="w-5 h-5 rounded-md border border-black/30"
                    style={{ background: GRADE_SWATCHES[grade] }}
                  />
                  {GRADE_LABELS[grade]}
                </button>
              ))}
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              <Toggle
                checked={draft.vignette}
                onChange={(v) => patch({ vignette: v })}
                label="Vignette"
                hint="Darkens the corners for a lens-like framing."
              />
              <Toggle
                checked={draft.film_grain}
                onChange={(v) => patch({ film_grain: v })}
                label="Film Grain"
                hint="Fine sensor noise so photographs do not read as stills."
              />
              <Toggle
                checked={draft.cinematic_bloom}
                onChange={(v) => patch({ cinematic_bloom: v })}
                label={REALISM_LABELS.cinematic_bloom.label}
                hint={REALISM_LABELS.cinematic_bloom.hint}
              />
              <Toggle
                checked={draft.letterbox}
                onChange={(v) => patch({ letterbox: v })}
                label={REALISM_LABELS.letterbox.label}
                hint={
                  draft.aspect_ratio === "16:9"
                    ? REALISM_LABELS.letterbox.hint
                    : "Scope bars apply to landscape output only."
                }
              />
            </div>
          </div>

          {/* Titles & labels */}
          <div className="space-y-3">
            <p className="text-[11px] font-bold uppercase tracking-wider text-[var(--text-3)] flex items-center gap-1.5">
              <Tag size={12} className="text-[var(--gold-1)]" /> Titles & Room Labels
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-2.5">
              <Toggle
                checked={draft.intro_title_enabled}
                onChange={(v) => patch({ intro_title_enabled: v })}
                label="Intro Card"
                hint="Opens on the property name with kinetic type."
              />
              <Toggle
                checked={draft.outro_enabled}
                onChange={(v) => patch({ outro_enabled: v })}
                label="Outro Card"
                hint="Closes the film with a branded card."
              />
              <Toggle
                checked={draft.room_labels_enabled}
                onChange={(v) => patch({ room_labels_enabled: v })}
                label="Room Labels"
                hint="Lower-third name on every room."
              />
              <Toggle
                checked={draft.room_counter}
                onChange={(v) => patch({ room_counter: v })}
                label="Room Counter"
                hint={REALISM_LABELS.room_counter.hint}
              />
            </div>
            {(draft.intro_title_enabled || draft.outro_enabled) && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-1">
                {draft.intro_title_enabled && (
                  <div className="space-y-2">
                    <label className="text-[11px] font-semibold text-[var(--text-2)]">
                      Intro headline (blank = property name)
                    </label>
                    <input
                      value={draft.intro_title_text ?? ""}
                      onChange={(e) => patch({ intro_title_text: e.target.value || null })}
                      placeholder="Luxury Property Walkthrough"
                      className="w-full px-3 py-2 rounded-xl bg-[var(--bg-0)] border border-[var(--border-1)] text-xs text-[var(--text-1)] focus:outline-none focus:border-[var(--gold-1)]"
                    />
                    <Slider
                      label="Intro length"
                      value={draft.intro_duration_seconds}
                      min={1}
                      max={6}
                      step={0.5}
                      suffix="s"
                      onChange={(v) => patch({ intro_duration_seconds: v })}
                    />
                  </div>
                )}
                {draft.outro_enabled && (
                  <div className="space-y-2">
                    <label className="text-[11px] font-semibold text-[var(--text-2)]">
                      Outro headline (blank = property name)
                    </label>
                    <input
                      value={draft.outro_text ?? ""}
                      onChange={(e) => patch({ outro_text: e.target.value || null })}
                      placeholder="Thank You"
                      className="w-full px-3 py-2 rounded-xl bg-[var(--bg-0)] border border-[var(--border-1)] text-xs text-[var(--text-1)] focus:outline-none focus:border-[var(--gold-1)]"
                    />
                    <Slider
                      label="Outro length"
                      value={draft.outro_duration_seconds}
                      min={1}
                      max={6}
                      step={0.5}
                      suffix="s"
                      onChange={(v) => patch({ outro_duration_seconds: v })}
                    />
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Brand mark */}
          <div className="space-y-2">
            <p className="text-[11px] font-bold uppercase tracking-wider text-[var(--text-3)] flex items-center gap-1.5">
              <Tag size={12} className="text-[var(--gold-1)]" /> Brand Mark
            </p>
            <input
              value={draft.brand_text ?? ""}
              onChange={(e) => patch({ brand_text: e.target.value || null })}
              placeholder="e.g. Sotheby's International Realty"
              className="w-full px-3 py-2 rounded-xl bg-[var(--bg-0)] border border-[var(--border-1)] text-xs text-[var(--text-1)] focus:outline-none focus:border-[var(--gold-1)]"
            />
            <p className="text-[10px] text-[var(--text-3)] leading-relaxed">
              Shown discreetly under the title and end cards. Leave blank to omit.
            </p>
          </div>

          {/* Music */}
          <div className="space-y-3">
            <p className="text-[11px] font-bold uppercase tracking-wider text-[var(--text-3)] flex items-center gap-1.5">
              <Music2 size={12} className="text-[var(--gold-1)]" /> Score
            </p>
            <Toggle
              checked={draft.music_enabled}
              onChange={(v) => patch({ music_enabled: v, music_style: v ? (draft.music_style === "none" ? "ambient" : draft.music_style) : "none" })}
              label="Background Score"
              hint="Generated on the server, so it is royalty-free with nothing to license."
            />
            {draft.music_enabled && (
              <div className="space-y-3 pl-1">
                <Segmented<MusicStyle>
                  value={draft.music_style}
                  onChange={(v) => patch({ music_style: v })}
                  options={(["ambient", "uplifting", "minimal_piano"] as MusicStyle[]).map((k) => ({
                    value: k,
                    label: MUSIC_LABELS[k],
                  }))}
                />
                <Slider
                  label="Score level"
                  value={draft.music_volume}
                  min={0}
                  max={1}
                  step={0.02}
                  suffix=""
                  onChange={(v) => patch({ music_volume: v })}
                />
              </div>
            )}
          </div>

          {/* Summary + actions */}
          <div className="pt-3 border-t border-[var(--border-1)] space-y-3">
            {estimate && (
              <p className="text-[11px] text-[var(--text-3)] flex items-center gap-1.5 flex-wrap">
                <Volume2 size={12} className="text-[var(--gold-1)]" />
                Renders at{" "}
                <span className="font-mono font-bold text-[var(--text-1)]">
                  {estimate.w}×{estimate.h}
                </span>{" "}
                @ {draft.fps}fps ·{" "}
                <span className="font-mono font-bold text-[var(--text-1)]">
                  ~{estimate.seconds.toFixed(1)}s
                </span>{" "}
                per room including cards ·{" "}
                {draft.music_enabled ? MUSIC_LABELS[draft.music_style] : "silent"}
              </p>
            )}

            {dirty && clipsAffected && (
              <div className="p-3 bg-amber-950/40 border border-amber-500/40 rounded-xl text-[11px] text-amber-200 flex items-start gap-2">
                <AlertTriangle size={13} className="mt-0.5 shrink-0 text-amber-400" />
                <span>
                  These changes reshape the clips themselves (length, frame shape, motion). Saved
                  clips will need to be regenerated to match.
                </span>
              </div>
            )}

            <div className="flex flex-wrap items-center justify-end gap-3">
              {dirty && (
                <button
                  type="button"
                  onClick={() => setDraft(saved)}
                  className="btn-ghost px-4 py-2 rounded-xl text-xs font-semibold"
                >
                  Discard
                </button>
              )}
              <button
                type="button"
                onClick={handleSave}
                disabled={saving || !dirty}
                className="btn-gold px-5 py-2 rounded-xl text-xs font-bold flex items-center gap-2 disabled:opacity-50"
              >
                {saving ? <Loader2 size={13} className="animate-spin" /> : <Save size={13} />}
                {saving ? "Saving…" : "Save Settings"}
              </button>
              {primaryAction && (
                <button
                  type="button"
                  onClick={primaryAction.onClick}
                  disabled={primaryAction.disabled}
                  className="btn-gold px-5 py-2 rounded-xl text-xs font-bold flex items-center gap-2 disabled:opacity-50"
                >
                  <Sparkles size={13} />
                  {primaryAction.label}
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {!open && dirty && (
        <div className="px-5 pb-4">
          <span className="text-[11px] text-amber-300">
            You have unsaved cinematic settings — open this panel to save them.
          </span>
        </div>
      )}
    </div>
  );
}
