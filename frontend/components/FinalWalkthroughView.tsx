"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { AssemblyConfig, AssemblyJob, FinalVideoMetadata } from "@/types/assembly";
import { ImmersiveSceneViewer } from "@/components/ImmersiveSceneViewer";
import { EvaluationSection } from "@/components/EvaluationSection";
import {
  Film,
  Play,
  Pause,
  Download,
  RotateCw,
  Clock,
  Layers,
  Sparkles,
  AlertTriangle,
  CheckCircle2,
  Loader2,
  ArrowLeft,
  Volume2,
  VolumeX,
  Maximize2,
  Settings2,
  Check,
  Compass,
  FileText,
} from "lucide-react";

interface FinalWalkthroughViewProps {
  projectId: string;
  propertyName?: string;
  onBackToClips: () => void;
}

export function FinalWalkthroughView({
  projectId,
  propertyName = "Property Walkthrough",
  onBackToClips,
}: FinalWalkthroughViewProps) {
  const [metadata, setMetadata] = useState<FinalVideoMetadata | null>(null);
  const [job, setJob] = useState<AssemblyJob | null>(null);
  const [loading, setLoading] = useState(true);
  const [isAssembling, setIsAssembling] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // View Mode: Cinematic Walkthrough Video vs Immersive Scene Viewer
  const [viewMode, setViewMode] = useState<"cinematic" | "immersive">("cinematic");

  // Configuration options
  const [showConfig, setShowConfig] = useState(false);
  const [includeIntro, setIncludeIntro] = useState(true);
  const [enableAudio, setEnableAudio] = useState(false);

  // Custom Player States
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);

  const fetchStatus = useCallback(async () => {
    try {
      const [metaRes, jobRes] = await Promise.all([
        api.getFinalVideoMetadata(projectId).catch(() => null),
        api.getAssemblyStatus(projectId).catch(() => null),
      ]);
      setMetadata(metaRes);
      setJob(jobRes);
      if (jobRes && (jobRes.status === "processing" || jobRes.status === "queued")) {
        setIsAssembling(true);
      } else {
        setIsAssembling(false);
      }
    } catch (err: unknown) {
      console.error("Failed to load assembly status:", err);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  // Polling while assembly is running
  useEffect(() => {
    if (!isAssembling) return;
    const interval = setInterval(() => {
      fetchStatus();
    }, 2000);
    return () => clearInterval(interval);
  }, [isAssembling, fetchStatus]);

  const handleAssemble = async (force: boolean = false) => {
    setError(null);
    setIsAssembling(true);
    try {
      const config: AssemblyConfig = {
        intro_title_enabled: includeIntro,
        audio_enabled: enableAudio,
        intro_duration_seconds: 1.5,
        crossfade_duration_seconds: 0.4,
      };
      const newJob = await api.assembleWalkthrough(projectId, {
        config,
        force_reassemble: force,
      });
      setJob(newJob);
      if (newJob.status === "completed" && newJob.result) {
        setMetadata(newJob.result);
        setIsAssembling(false);
      }
    } catch (err: unknown) {
      const e = err as { message?: string };
      setError(e.message || "Failed to assemble walkthrough video.");
      setIsAssembling(false);
    }
  };

  // Video controls handlers
  const togglePlay = () => {
    if (!videoRef.current) return;
    if (isPlaying) {
      videoRef.current.pause();
    } else {
      videoRef.current.play();
    }
  };

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseFloat(e.target.value);
    if (videoRef.current) {
      videoRef.current.currentTime = val;
      setCurrentTime(val);
    }
  };

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseFloat(e.target.value);
    setVolume(val);
    if (videoRef.current) {
      videoRef.current.volume = val;
      setIsMuted(val === 0);
    }
  };

  const toggleMute = () => {
    if (!videoRef.current) return;
    if (isMuted) {
      videoRef.current.muted = false;
      setIsMuted(false);
    } else {
      videoRef.current.muted = true;
      setIsMuted(true);
    }
  };

  const toggleFullscreen = () => {
    if (!videoRef.current) return;
    if (document.fullscreenElement) {
      document.exitFullscreen();
    } else {
      videoRef.current.requestFullscreen();
    }
  };

  const formatTime = (secs: number) => {
    const mins = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${mins.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-28 space-y-4">
        <div className="w-12 h-12 border-3 border-[var(--gold-dim)] border-t-[var(--gold-1)] rounded-full animate-spin" />
        <p className="text-sm font-medium text-[var(--text-2)]">Loading property walkthrough…</p>
      </div>
    );
  }

  const finalVideoUrl = api.getFinalVideoUrl(projectId);
  const downloadUrl = api.getFinalVideoDownloadUrl(projectId);

  return (
    <div className="space-y-8 anim-fade-up max-w-6xl mx-auto pb-16">
      {/* ── Header Bar ── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 glass-gold p-6 md:p-8 rounded-3xl border border-[var(--border-2)] shadow-xl">
        <div className="space-y-2">
          <div className="flex items-center gap-3">
            <button
              onClick={onBackToClips}
              className="btn-ghost px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5"
            >
              <ArrowLeft className="w-4 h-4" />
              Clip Studio
            </button>
            <span className="badge badge-gold font-mono font-bold">
              Phase 06 · Immersive Viewer & Evaluation
            </span>
            {metadata && !metadata.is_outdated && (
              <span className="badge badge-success font-semibold flex items-center gap-1">
                <Check size={12} /> Ready for Delivery
              </span>
            )}
          </div>
          <h1 className="text-2xl md:text-4xl font-bold font-display text-[var(--text-1)]">
            {propertyName}
          </h1>
          <p className="text-sm text-[var(--text-2)] max-w-2xl leading-relaxed">
            Experience the generated real estate walkthrough in cinematic playback or interactively inspect scenes in 360° / immersive pan-zoom view.
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={() => setShowConfig(!showConfig)}
            className="btn-ghost px-4 py-2.5 rounded-xl text-xs font-semibold flex items-center gap-2 border border-[var(--border-1)]"
          >
            <Settings2 className="w-4 h-4 text-[var(--gold-2)]" />
            Assembly Settings
          </button>

          {metadata && !metadata.is_outdated ? (
            <a
              href={downloadUrl}
              download
              className="btn-gold px-6 py-3 rounded-xl font-bold text-sm flex items-center gap-2 shadow-lg glow-gold"
            >
              <Download className="w-4 h-4" />
              Download Walkthrough MP4
            </a>
          ) : (
            <button
              onClick={() => handleAssemble(true)}
              disabled={isAssembling}
              className="btn-gold px-6 py-3 rounded-xl font-bold text-sm flex items-center gap-2 shadow-lg glow-gold disabled:opacity-50"
            >
              {isAssembling ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Assembling Walkthrough…
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4 fill-current" />
                  {metadata?.is_outdated ? "Reassemble Walkthrough" : "Generate Final Walkthrough"}
                </>
              )}
            </button>
          )}
        </div>
      </div>

      {/* Assembly Settings Drawer */}
      {showConfig && (
        <div className="glass rounded-2xl p-6 border border-[var(--border-2)] anim-fade-down space-y-4">
          <div className="flex items-center justify-between border-b border-[var(--border-1)] pb-3">
            <h4 className="text-sm font-bold text-[var(--text-1)] flex items-center gap-2">
              <Settings2 className="w-4 h-4 text-[var(--gold-1)]" />
              Assembly Configuration & Options
            </h4>
            <span className="text-xs text-[var(--text-3)] font-mono">Real-time FFmpeg engine pipeline</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
            <label className="flex items-start gap-3 p-3.5 rounded-xl bg-[var(--bg-0)] border border-[var(--border-1)] cursor-pointer hover:border-[var(--border-2)] transition-colors">
              <input
                type="checkbox"
                checked={includeIntro}
                onChange={(e) => setIncludeIntro(e.target.checked)}
                className="mt-1 rounded border-[var(--border-2)] text-[var(--gold-1)] focus:ring-[var(--gold-1)]"
              />
              <div>
                <p className="text-xs font-semibold text-[var(--text-1)]">Include Title Intro Card</p>
                <p className="text-[11px] text-[var(--text-3)] mt-0.5">
                  Displays property name and subtitle for 1.5s before the first scene clip.
                </p>
              </div>
            </label>

            <label className="flex items-start gap-3 p-3.5 rounded-xl bg-[var(--bg-0)] border border-[var(--border-1)] cursor-pointer hover:border-[var(--border-2)] transition-colors">
              <input
                type="checkbox"
                checked={enableAudio}
                onChange={(e) => setEnableAudio(e.target.checked)}
                className="mt-1 rounded border-[var(--border-2)] text-[var(--gold-1)] focus:ring-[var(--gold-1)]"
              />
              <div>
                <p className="text-xs font-semibold text-[var(--text-1)]">Optional Ambient Background Track</p>
                <p className="text-[11px] text-[var(--text-3)] mt-0.5">
                  Subtle, balanced ambient property soundscape. (Disabled by default).
                </p>
              </div>
            </label>
          </div>

          <div className="flex justify-end pt-2">
            <button
              onClick={() => {
                setShowConfig(false);
                handleAssemble(true);
              }}
              disabled={isAssembling}
              className="btn-gold px-5 py-2 rounded-xl text-xs font-bold flex items-center gap-2"
            >
              <RotateCw className="w-3.5 h-3.5" />
              Apply & Reassemble
            </button>
          </div>
        </div>
      )}

      {/* Outdated Warning Banner */}
      {metadata?.is_outdated && (
        <div className="p-4 bg-amber-950/40 border border-amber-500/40 rounded-2xl flex flex-col sm:flex-row sm:items-center justify-between gap-4 text-amber-200">
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 shrink-0 text-amber-400" />
            <div>
              <p className="text-xs font-bold text-amber-300">Plan Modified Since Last Assembly</p>
              <p className="text-[11px] text-amber-200/80">
                Scene order or motion settings were updated. Reassemble to update the walkthrough video.
              </p>
            </div>
          </div>
          <button
            onClick={() => handleAssemble(true)}
            disabled={isAssembling}
            className="btn-gold px-4 py-2 rounded-xl text-xs font-bold whitespace-nowrap self-start sm:self-auto"
          >
            Reassemble Now
          </button>
        </div>
      )}

      {/* Assembly Error Banner */}
      {error && (
        <div className="p-4 bg-red-950/50 border border-red-500/30 rounded-2xl flex items-center justify-between text-red-300 text-sm">
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 shrink-0 text-red-400" />
            <span>{error}</span>
          </div>
          <button
            onClick={() => handleAssemble(true)}
            className="btn-ghost text-xs font-bold text-red-300 hover:text-white underline"
          >
            Retry Assembly
          </button>
        </div>
      )}

      {/* ── Assembling Progress State ── */}
      {isAssembling && (
        <div className="glass-gold rounded-3xl p-8 border border-[var(--border-2)] text-center space-y-6">
          <div className="relative w-16 h-16 mx-auto">
            <div className="w-16 h-16 rounded-full border-4 border-[var(--border-1)] border-t-[var(--gold-1)] animate-spin" />
            <Film className="w-6 h-6 text-[var(--gold-1)] absolute inset-0 m-auto" />
          </div>

          <div className="space-y-2 max-w-md mx-auto">
            <h3 className="text-lg font-bold text-[var(--text-1)] font-display">
              {job?.stage_message || "Assembling Property Walkthrough Video..."}
            </h3>
            <p className="text-xs text-[var(--text-3)] font-mono">
              Stage: {job?.stage?.replace(/_/g, " ").toUpperCase() || "PROCESSING"} ({job?.progress_percentage || 50}%)
            </p>
          </div>

          {/* Real progress bar */}
          <div className="w-full max-w-lg mx-auto h-2 bg-[var(--bg-0)] rounded-full overflow-hidden border border-[var(--border-1)]">
            <div
              className="h-full bg-gradient-to-r from-[var(--gold-1)] to-[var(--gold-3)] transition-all duration-500 rounded-full"
              style={{ width: `${job?.progress_percentage || 45}%` }}
            />
          </div>

          {/* Stage steps checklist */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 max-w-2xl mx-auto pt-4 text-left">
            <div className="p-3 bg-[var(--bg-0)] rounded-xl border border-[var(--border-1)] text-xs">
              <span className="text-[var(--gold-1)] font-mono font-bold block mb-1">01 Validate</span>
              <span className="text-[11px] text-[var(--text-2)]">Verify clip streams</span>
            </div>
            <div className="p-3 bg-[var(--bg-0)] rounded-xl border border-[var(--border-1)] text-xs">
              <span className="text-[var(--gold-1)] font-mono font-bold block mb-1">02 Normalize</span>
              <span className="text-[11px] text-[var(--text-2)]">Uniform H.264 / 24fps</span>
            </div>
            <div className="p-3 bg-[var(--bg-0)] rounded-xl border border-[var(--border-1)] text-xs">
              <span className="text-[var(--gold-1)] font-mono font-bold block mb-1">03 Concat</span>
              <span className="text-[11px] text-[var(--text-2)]">Restrained transitions</span>
            </div>
            <div className="p-3 bg-[var(--bg-0)] rounded-xl border border-[var(--border-1)] text-xs">
              <span className="text-[var(--gold-1)] font-mono font-bold block mb-1">04 Verify</span>
              <span className="text-[11px] text-[var(--text-2)]">FFprobe validation</span>
            </div>
          </div>
        </div>
      )}

      {/* ── Mode Selection Pill Switcher ── */}
      <div className="flex items-center justify-center">
        <div className="inline-flex p-1.5 rounded-2xl bg-[var(--bg-1)] border border-[var(--border-2)] shadow-md">
          <button
            onClick={() => setViewMode("cinematic")}
            className={`px-5 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 ${
              viewMode === "cinematic"
                ? "bg-[var(--gold-1)] text-white shadow-md"
                : "text-[var(--text-2)] hover:text-[var(--text-1)]"
            }`}
          >
            <Film className="w-4 h-4" />
            Cinematic Walkthrough
          </button>
          <button
            onClick={() => setViewMode("immersive")}
            className={`px-5 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 ${
              viewMode === "immersive"
                ? "bg-[var(--gold-1)] text-white shadow-md"
                : "text-[var(--text-2)] hover:text-[var(--text-1)]"
            }`}
          >
            <Compass className="w-4 h-4" />
            Immersive Scene Viewer (360° / Pan-Zoom)
          </button>
        </div>
      </div>

      {/* ── View 1: Cinematic Walkthrough Video Experience ── */}
      {viewMode === "cinematic" && !isAssembling && metadata && (
        <div className="space-y-6">
          <div className="glass-card rounded-3xl overflow-hidden border border-[var(--border-2)] shadow-2xl relative">
            {/* Aspect Ratio Container for Video */}
            <div className="relative aspect-video bg-black flex items-center justify-center group">
              <video
                ref={videoRef}
                src={finalVideoUrl}
                preload="metadata"
                playsInline
                className="w-full h-full object-contain"
                onTimeUpdate={() => {
                  if (videoRef.current) {
                    setCurrentTime(videoRef.current.currentTime);
                  }
                }}
                onLoadedMetadata={() => {
                  if (videoRef.current) {
                    setDuration(videoRef.current.duration);
                  }
                }}
                onPlay={() => setIsPlaying(true)}
                onPause={() => setIsPlaying(false)}
                onEnded={() => setIsPlaying(false)}
                onClick={togglePlay}
              />

              {/* Big Play Overlay if paused */}
              {!isPlaying && (
                <button
                  onClick={togglePlay}
                  className="absolute inset-0 m-auto w-20 h-20 rounded-full bg-[var(--gold-1)]/90 text-black flex items-center justify-center shadow-2xl hover:scale-110 transition-transform duration-300"
                >
                  <Play className="w-8 h-8 fill-current ml-1" />
                </button>
              )}

              {/* Video Player Custom HUD Controls */}
              <div className="absolute bottom-0 inset-x-0 bg-gradient-to-t from-black/90 via-black/50 to-transparent p-4 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                {/* Seek Bar */}
                <input
                  type="range"
                  min={0}
                  max={duration || 100}
                  step={0.1}
                  value={currentTime}
                  onChange={handleSeek}
                  className="w-full h-1.5 bg-white/20 rounded-lg appearance-none cursor-pointer accent-[var(--gold-1)] mb-3"
                />

                <div className="flex items-center justify-between text-white text-xs">
                  <div className="flex items-center gap-4">
                    <button
                      onClick={togglePlay}
                      className="hover:text-[var(--gold-1)] transition-colors"
                    >
                      {isPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5" />}
                    </button>

                    <div className="flex items-center gap-2">
                      <button onClick={toggleMute} className="hover:text-[var(--gold-1)]">
                        {isMuted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
                      </button>
                      <input
                        type="range"
                        min={0}
                        max={1}
                        step={0.05}
                        value={isMuted ? 0 : volume}
                        onChange={handleVolumeChange}
                        className="w-16 h-1 bg-white/30 rounded accent-[var(--gold-1)] cursor-pointer hidden sm:block"
                      />
                    </div>

                    <span className="font-mono text-[11px] text-white/80">
                      {formatTime(currentTime)} / {formatTime(duration)}
                    </span>
                  </div>

                  <div className="flex items-center gap-4">
                    <button
                      onClick={toggleFullscreen}
                      className="hover:text-[var(--gold-1)] transition-colors p-1"
                    >
                      <Maximize2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            </div>

            {/* Video Metrics Strip */}
            <div className="bg-[var(--bg-0)] p-4 md:p-6 border-t border-[var(--border-1)] flex flex-wrap items-center justify-between gap-4">
              <div className="flex flex-wrap items-center gap-6">
                <div className="flex items-center gap-2 text-xs">
                  <Clock className="w-4 h-4 text-[var(--gold-1)]" />
                  <span className="text-[var(--text-3)]">Duration:</span>
                  <span className="font-bold text-[var(--text-1)] font-mono">
                    {metadata.duration_seconds.toFixed(1)}s ({formatTime(metadata.duration_seconds)})
                  </span>
                </div>

                <div className="flex items-center gap-2 text-xs">
                  <Layers className="w-4 h-4 text-[var(--gold-1)]" />
                  <span className="text-[var(--text-3)]">Scenes:</span>
                  <span className="font-bold text-[var(--text-1)] font-mono">
                    {metadata.scene_count} rooms assembled
                  </span>
                </div>

                <div className="flex items-center gap-2 text-xs">
                  <Film className="w-4 h-4 text-[var(--gold-1)]" />
                  <span className="text-[var(--text-3)]">Codec:</span>
                  <span className="font-bold text-[var(--text-1)] uppercase font-mono">
                    {metadata.video_codec} ({metadata.format})
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <a
                  href={downloadUrl}
                  download
                  className="btn-gold px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-2"
                >
                  <Download className="w-3.5 h-3.5" />
                  Download (.mp4)
                </a>
              </div>
            </div>
          </div>

          {/* ── Ordered Scene Sequence Breakdown ── */}
          <div className="space-y-4 pt-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-bold font-display text-[var(--text-1)]">
                  Walkthrough Sequence ({metadata.scenes_in_order.length} Scenes)
                </h3>
                <p className="text-xs text-[var(--text-3)]">
                  Exact architectural walkthrough ordering approved in Generation Plan.
                </p>
              </div>
              <span className="badge badge-gold font-mono text-[10px]">
                Plan v{metadata.plan_version}
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {metadata.scenes_in_order.map((scene) => (
                <div
                  key={scene.scene_id}
                  className="glass rounded-2xl p-4 border border-[var(--border-1)] flex items-center gap-4 hover:border-[var(--border-2)] transition-colors"
                >
                  <div className="w-10 h-10 rounded-xl bg-[var(--gold-dim)] text-[var(--gold-1)] flex items-center justify-center font-display font-bold text-sm shrink-0 border border-[var(--border-2)]">
                    {String(scene.order).padStart(2, "0")}
                  </div>

                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-bold text-[var(--text-1)] truncate">
                      {scene.label}
                    </p>
                    <p className="text-[11px] text-[var(--text-3)] capitalize mt-0.5">
                      {scene.scene_type.replace(/_/g, " ")} · {scene.duration_seconds.toFixed(1)}s
                    </p>
                  </div>

                  <div className="text-right">
                    <span className="text-[10px] font-mono text-[var(--gold-2)] bg-[var(--bg-0)] px-2 py-1 rounded-md border border-[var(--border-1)]">
                      {scene.transition_to_next.replace(/_/g, " ")}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* No Video Assembled Yet Prompt (for Cinematic Mode) */}
      {viewMode === "cinematic" && !isAssembling && !metadata && (
        <div className="glass-gold rounded-3xl p-16 text-center max-w-xl mx-auto border border-[var(--border-2)] space-y-6">
          <Film className="w-16 h-16 text-[var(--gold-1)] mx-auto" />
          <div className="space-y-2">
            <h3 className="font-display text-2xl font-bold text-[var(--text-1)]">
              Ready for Final Walkthrough Assembly
            </h3>
            <p className="text-xs text-[var(--text-2)] leading-relaxed max-w-md mx-auto">
              All scene clips are generated and validated. Concatenate them into a single high-definition property walkthrough with restrained transitions.
            </p>
          </div>

          <button
            onClick={() => handleAssemble(false)}
            disabled={isAssembling}
            className="btn-gold px-8 py-3.5 rounded-xl font-bold text-sm shadow-xl glow-gold inline-flex items-center gap-2"
          >
            <Sparkles className="w-4 h-4 fill-current" />
            Assemble Walkthrough Video
          </button>
        </div>
      )}

      {/* ── View 2: Immersive Scene Viewer Experience ── */}
      {viewMode === "immersive" && (
        <div className="space-y-6 anim-fade-in">
          <ImmersiveSceneViewer projectId={projectId} />
        </div>
      )}

      {/* ── Bottom Section: Phase 6 Quality Evaluation & Audit ── */}
      <EvaluationSection
        projectId={projectId}
        propertyName={propertyName}
      />
    </div>
  );
}
