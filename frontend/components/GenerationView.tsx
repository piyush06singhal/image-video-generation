"use client";

import React, { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import {
  ProjectGenerationOverview,
  SceneGenerationSummary,
} from "@/types/generation";
import { SceneGenerationCard } from "./SceneGenerationCard";
import { VideoPlayerModal } from "./VideoPlayerModal";
import { RenderOptionsPanel } from "./RenderOptionsPanel";
import { countFallbackClips, describeEngine } from "@/lib/providers";
import {
  Play,
  ArrowLeft,
  Sparkles,
  Loader2,
  AlertTriangle,
  Cpu,
} from "lucide-react";

interface GenerationViewProps {
  projectId: string;
  onBackToPlan: () => void;
  onProceedToPhase5?: () => void;
}

export function GenerationView({ projectId, onBackToPlan, onProceedToPhase5 }: GenerationViewProps) {
  const [overview, setOverview] = useState<ProjectGenerationOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
  const [forceRegenerate, setForceRegenerate] = useState(false);
  const [selectedSceneIds, setSelectedSceneIds] = useState<string[]>([]);
  const [isCreatingFallback, setIsCreatingFallback] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Video preview modal state
  const [selectedPreviewScene, setSelectedPreviewScene] = useState<SceneGenerationSummary | null>(null);

  const fetchOverview = useCallback(async () => {
    try {
      const data = await api.getGenerationOverview(projectId);
      setOverview(data);
      setIsGenerating(data.generating_scenes > 0);
    } catch (err: unknown) {
      console.error("Failed to load generation overview:", err);
      const e = err as { message?: string };
      setError(e.message || "Failed to load generation overview");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    let isMounted = true;
    const load = async () => {
      try {
        const data = await api.getGenerationOverview(projectId);
        if (isMounted) {
          setOverview(data);
          setIsGenerating(data.generating_scenes > 0);
          setLoading(false);
        }
      } catch (err: unknown) {
        if (isMounted) {
          const e = err as { message?: string };
          setError(e.message || "Failed to load generation overview");
          setLoading(false);
        }
      }
    };
    load();
    return () => {
      isMounted = false;
    };
  }, [projectId]);

  // Polling loop while any clips are actively generating
  useEffect(() => {
    if (!overview || overview.generating_scenes === 0) return;

    const interval = setInterval(() => {
      fetchOverview();
    }, 3000);

    return () => clearInterval(interval);
  }, [overview, fetchOverview]);

  const handleGenerateAll = async () => {
    setError(null);
    setIsGenerating(true);
    try {
      const updated = await api.generateClips(projectId, {
        force_regenerate: forceRegenerate,
      });
      setOverview(updated);
    } catch (err: unknown) {
      const e = err as { message?: string };
      setError(e.message || "Video generation failed to initialize");
      setIsGenerating(false);
    }
  };

  const handleGenerateSelected = async () => {
    if (!selectedSceneIds.length) return;
    setError(null);
    setIsGenerating(true);
    try {
      setOverview(await api.generateClips(projectId, {
        scene_ids: selectedSceneIds,
        force_regenerate: forceRegenerate,
      }));
      setSelectedSceneIds([]);
    } catch (err: unknown) {
      const e = err as { message?: string };
      setError(e.message || "Selected generation failed to initialize");
      setIsGenerating(false);
    }
  };

  const handleLocalSlideshow = async () => {
    setError(null);
    setIsCreatingFallback(true);
    try {
      await api.createLocalSlideshow(projectId);
      if (onProceedToPhase5) onProceedToPhase5();
    } catch (err: unknown) {
      const e = err as { message?: string };
      setError(e.message || "Could not create the local slideshow fallback");
    } finally {
      setIsCreatingFallback(false);
    }
  };

  const handleRetryJob = async (jobId: string) => {
    setError(null);
    try {
      await api.retryJob(projectId, jobId);
      await fetchOverview();
    } catch (err: unknown) {
      const e = err as { message?: string };
      setError(e.message || "Failed to retry generation job");
    }
  };

  const handleRegenerateScene = async (sceneId: string, customMotion?: string) => {
    setError(null);
    try {
      await api.regenerateSceneClip(projectId, sceneId, {
        custom_motion_type: customMotion,
      });
      await fetchOverview();
    } catch (err: unknown) {
      const e = err as { message?: string };
      setError(e.message || "Failed to trigger scene regeneration");
    }
  };

  if (loading && !overview) {
    return (
      <div className="flex flex-col items-center justify-center py-24 space-y-4">
        <div className="w-10 h-10 border-2 border-[var(--gold-dim)] border-t-[var(--gold-1)] rounded-full animate-spin" />
        <p className="text-[var(--text-2)] text-sm font-medium">Loading generation studio…</p>
      </div>
    );
  }

  const completedPct = overview && overview.total_scenes > 0
    ? Math.round((overview.completed_scenes / overview.total_scenes) * 100)
    : 0;

  // Which engine is configured, and did any clip actually fall back to the local
  // renderer? Surfacing the mismatch stops a quality difference looking like a bug.
  const engine = describeEngine(overview?.active_provider);
  const fallbackCount = overview
    ? countFallbackClips(overview.scenes.map((scene) => scene.clip), overview.active_provider)
    : 0;
  // Clips rendered under older settings are reported by the backend; they must be
  // regenerated before the walkthrough will match the chosen look.
  const clipsOutdated = Boolean(overview?.clips_outdated && overview.completed_scenes > 0);

  return (
    <div className="space-y-8 anim-fade-up">
      {/* Top Header & Overview Banner */}
      <div className="glass-gold rounded-3xl p-6 md:p-8 border border-[var(--border-2)] relative overflow-hidden shadow-2xl">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 relative z-10">
          <div className="space-y-2">
            <div className="flex items-center gap-3">
              <button
                onClick={onBackToPlan}
                className="btn-ghost px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5"
              >
                <ArrowLeft className="w-4 h-4" />
                Edit Plan
              </button>
              <span className="badge badge-gold font-mono font-bold">
                Phase 04
              </span>
            </div>
            <h2 className="text-2xl md:text-3xl font-bold font-display text-[var(--text-1)]">
              Image-to-Video Clip Generation
            </h2>
            <p className="text-sm text-[var(--text-2)] max-w-2xl leading-relaxed">
              Transforming your structured walkthrough scenes into restrained, cinematic video clips using the{" "}
              <span className="text-[var(--text-1)] font-semibold">{engine.label}</span> engine.
            </p>
          </div>

          {clipsOutdated && (
            <div className="mt-5 rounded-xl border border-amber-500/40 bg-amber-950/30 px-4 py-3 text-sm text-amber-200 flex flex-col sm:flex-row sm:items-center gap-3 justify-between">
              <span className="flex items-start gap-2">
                <AlertTriangle size={15} className="mt-0.5 shrink-0 text-amber-400" />
                <span>
                  {overview?.completed_scenes} existing clip
                  {overview?.completed_scenes === 1 ? " was" : "s were"} rendered with different
                  cinematic settings than the project now uses. Regenerate to apply the current
                  settings.
                </span>
              </span>
              <button
                onClick={() => {
                  setForceRegenerate(true);
                  void handleGenerateAll();
                }}
                disabled={isGenerating}
                className="btn-gold px-4 py-2 rounded-xl text-xs font-bold whitespace-nowrap disabled:opacity-50"
              >
                Regenerate All Clips
              </button>
            </div>
          )}

          {/* Cinematic settings live here so the look is chosen before spending time on clips */}
          <div className="mt-8">
            <RenderOptionsPanel
              projectId={projectId}
              onSaved={() => {
                void fetchOverview();
              }}
            />
          </div>

          {/* Action Trigger */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
            <label className="flex items-center gap-2 text-xs text-[var(--text-2)] cursor-pointer select-none bg-[var(--bg-0)] px-3 py-2 rounded-xl border border-[var(--border-1)]">
              <input
                type="checkbox"
                checked={forceRegenerate}
                onChange={(e) => setForceRegenerate(e.target.checked)}
                className="rounded border-[var(--border-2)] text-[var(--gold-1)]"
              />
              <span>Force Regenerate All</span>
            </label>

            <button
              onClick={handleGenerateAll}
              disabled={isGenerating || Boolean(overview?.scenes.some((scene) => scene.status === "paused"))}
              className="btn-ghost px-5 py-3 rounded-xl font-bold text-sm transition-all flex items-center justify-center gap-2 border border-[var(--border-2)] disabled:opacity-50"
            >
              {isGenerating ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Generating Clips ({overview?.generating_scenes || 0} active)…
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 fill-current" />
                  {overview && overview.completed_scenes > 0
                    ? `Generate Missing Clips (${overview.pending_scenes + overview.failed_scenes})`
                    : "Generate All Clips"}
                </>
              )}
            </button>
            <button
              onClick={handleGenerateSelected}
              disabled={isGenerating || selectedSceneIds.length === 0}
              className="btn-ghost px-4 py-3 rounded-xl font-bold text-sm disabled:opacity-50"
            >
              Generate Selected ({selectedSceneIds.length})
            </button>
            <button
              onClick={handleLocalSlideshow}
              disabled={isCreatingFallback}
              className="btn-ghost px-4 py-3 rounded-xl font-bold text-sm border border-[var(--border-2)] disabled:opacity-50"
            >
              {isCreatingFallback ? "Creating fallback…" : "Use Image Slideshow"}
            </button>

            {overview && overview.completed_scenes > 0 && onProceedToPhase5 && (
              <button
                onClick={onProceedToPhase5}
                className="btn-gold px-6 py-3 rounded-xl font-bold text-sm transition-all flex items-center justify-center gap-2 shadow-lg glow-gold"
              >
                <Sparkles className="w-4 h-4" />
                Assemble Final Walkthrough (Phase 5) →
              </button>
            )}
          </div>
          {overview?.status === "paused" && (
            <div className="mt-5 rounded-xl border border-[var(--amber)]/30 bg-[var(--amber-dim)] px-4 py-3 text-sm text-[var(--text-2)]">
              Free-tier provider quota is paused. Wait for the provider quota window to reset, then use the scene Retry buttons. You can also create the local image slideshow now. Duplicate batch jobs are blocked while a scene is queued, processing, or paused.
            </div>
          )}
          {fallbackCount > 0 && overview?.status !== "paused" && (
            <div className="mt-5 rounded-xl border border-[var(--border-2)] bg-[var(--bg-0)] px-4 py-3 text-sm text-[var(--text-2)]">
              {fallbackCount} of {overview?.completed_scenes} clip
              {overview?.completed_scenes === 1 ? " was" : "s were"} rendered by the local fallback
              renderer because the {engine.label} engine was unavailable (quota, rate limit, or
              configuration). Those clips move a camera over your original photographs, so the
              property is reproduced exactly. Retry a scene to try the {engine.label} engine again.
            </div>
          )}
        </div>

        {/* Stats Metrics Bar */}
        {overview && (
          <div className="mt-8 pt-6 border-t border-[var(--border-1)] grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="bg-[var(--bg-0)] p-4 rounded-2xl border border-[var(--border-1)]">
              <span className="text-[10px] font-mono text-[var(--gold-1)] uppercase block font-bold">Progress</span>
              <div className="flex items-baseline gap-2 mt-1">
                <span className="text-2xl font-bold text-[var(--text-1)] font-display">{completedPct}%</span>
                <span className="text-xs text-[var(--text-3)]">({overview.completed_scenes}/{overview.total_scenes} clips)</span>
              </div>
              {/* Progress Bar */}
              <div className="mt-2 w-full h-1.5 bg-[var(--bg-card)] rounded-full overflow-hidden border border-[var(--border-1)]">
                <div
                  className="h-full bg-gradient-to-r from-[var(--gold-1)] to-[var(--gold-3)] transition-all duration-500 rounded-full"
                  style={{ width: `${completedPct}%` }}
                />
              </div>
            </div>

            <div className="bg-[var(--bg-0)] p-4 rounded-2xl border border-[var(--border-1)]">
              <span className="text-[10px] font-mono text-[var(--gold-1)] uppercase block font-bold">Total Video Length</span>
              <span className="text-2xl font-bold text-[var(--text-1)] font-display mt-1 block">
                {overview.total_duration_seconds.toFixed(1)}s
              </span>
              <span className="text-xs text-[var(--text-3)] block mt-0.5">High-definition MP4</span>
            </div>

            <div className="bg-[var(--bg-0)] p-4 rounded-2xl border border-[var(--border-1)]">
              <span className="text-[10px] font-mono text-[var(--gold-1)] uppercase block font-bold">Engine</span>
              <span className="text-base font-semibold text-[var(--text-1)] mt-1 block flex items-center gap-1.5">
                {engine.kind === "plate" ? (
                  <Cpu className="w-3.5 h-3.5 text-[var(--gold-2)]" />
                ) : (
                  <Sparkles className="w-3.5 h-3.5 text-[var(--gold-2)]" />
                )}
                {engine.label}
              </span>
              <span className="text-xs text-[var(--text-3)] block mt-0.5">{engine.description}</span>
              {fallbackCount > 0 && (
                <span className="text-[10px] font-mono text-amber-300 block mt-0.5">
                  {fallbackCount} clip{fallbackCount === 1 ? "" : "s"} rendered locally
                </span>
              )}
            </div>

            <div className="bg-[var(--bg-0)] p-4 rounded-2xl border border-[var(--border-1)]">
              <span className="text-[10px] font-mono text-[var(--gold-1)] uppercase block font-bold">Pipeline State</span>
              <span className="text-base font-semibold text-[var(--text-1)] mt-1 block capitalize">
                {overview.status.replace(/_/g, " ")}
              </span>
              <span className="text-xs text-[var(--text-3)] block mt-0.5">
                {overview.failed_scenes > 0 ? `${overview.failed_scenes} failed (retry ready)` : "All systems optimal"}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Error alert */}
      {error && (
        <div className="p-4 bg-red-950/50 border border-red-500/30 rounded-2xl flex items-center justify-between text-red-300 text-sm">
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 shrink-0 text-red-400" />
            <span>{error}</span>
          </div>
          <button
            onClick={() => setError(null)}
            className="text-red-300 hover:text-white text-xs font-mono underline"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Scenes Clip Generation Grid */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-bold font-display text-[var(--text-1)]">
            Planned Scene Clips ({overview?.scenes.length || 0})
          </h3>
          <span className="text-xs text-[var(--text-3)] font-mono">
            {engine.kind === "plate"
              ? "Camera motion over your original photographs — geometry preserved exactly"
              : "Generated clips keep the source photo as a visual guide"}
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {overview?.scenes.map((scene) => (
            <div key={scene.scene_id} className="relative">
              <label className="absolute left-4 top-4 z-10 flex items-center gap-2 rounded-lg bg-white/90 px-2 py-1 text-xs font-semibold text-[var(--text-2)]">
                <input
                  type="checkbox"
                  checked={selectedSceneIds.includes(scene.scene_id)}
                  onChange={(event) => setSelectedSceneIds((current) =>
                    event.target.checked
                      ? [...current, scene.scene_id]
                      : current.filter((id) => id !== scene.scene_id)
                  )}
                />
                Select
              </label>
              <SceneGenerationCard
                scene={scene}
                projectId={projectId}
                activeProvider={overview?.active_provider}
                activeModel={overview?.active_model}
                onPreview={(s) => setSelectedPreviewScene(s)}
                onRetry={handleRetryJob}
                onRegenerate={handleRegenerateScene}
              />
            </div>
          ))}
        </div>
      </div>

      {/* Video Preview Modal */}
      <VideoPlayerModal
        isOpen={Boolean(selectedPreviewScene && selectedPreviewScene.clip)}
        projectId={projectId}
        sceneLabel={selectedPreviewScene?.label || "Scene Clip"}
        clip={selectedPreviewScene?.clip || null}
        onClose={() => setSelectedPreviewScene(null)}
      />
    </div>
  );
}
