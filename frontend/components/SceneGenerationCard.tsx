"use client";

import React, { useState } from "react";
import Image from "next/image";
import { SceneGenerationSummary } from "@/types/generation";
import {
  Play,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  Loader2,
  Video,
  Sparkles,
} from "lucide-react";

interface SceneGenerationCardProps {
  scene: SceneGenerationSummary;
  projectId?: string;
  onPreview: (scene: SceneGenerationSummary) => void;
  onRetry: (jobId: string) => void;
  onRegenerate: (sceneId: string, customMotion?: string) => void;
}

const MOTION_OPTIONS = [
  { value: "slow_forward", label: "Slow Forward Dolly" },
  { value: "slow_backward", label: "Slow Backward Pull" },
  { value: "pan_left", label: "Smooth Pan Left" },
  { value: "pan_right", label: "Smooth Pan Right" },
  { value: "static_subtle_motion", label: "Static Subtle Motion" },
  { value: "gentle_orbit", label: "Gentle Arc Orbit" },
];

export function SceneGenerationCard({
  scene,
  onPreview,
  onRetry,
  onRegenerate,
}: SceneGenerationCardProps) {
  const [showMotionMenu, setShowMotionMenu] = useState(false);
  const [isRetrying, setIsRetrying] = useState(false);

  const handleRetryClick = async () => {
    if (!scene.job_id) return;
    setIsRetrying(true);
    try {
      await onRetry(scene.job_id);
    } finally {
      setIsRetrying(false);
    }
  };

  const handleRegenSelect = (motion: string) => {
    setShowMotionMenu(false);
    onRegenerate(scene.scene_id, motion);
  };

  return (
    <div
      className={`glass-gold relative group rounded-2xl border transition-all duration-200 overflow-hidden flex flex-col card-hover ${
        scene.status === "completed"
          ? "border-emerald-500/30 shadow-lg"
          : scene.status === "generating"
          ? "border-[var(--gold-2)] shadow-[0_0_20px_var(--gold-glow)] animate-pulse"
          : scene.status === "failed"
          ? "border-red-500/40"
          : scene.status === "paused"
          ? "border-amber-500/40"
          : "border-[var(--border-1)]"
      }`}
    >
      {/* Top Image Preview & Status Overlay */}
      <div className="relative aspect-video w-full bg-[var(--bg-0)] overflow-hidden">
        {scene.thumbnail_url ? (
          <Image
            src={scene.thumbnail_url}
            alt={scene.label}
            fill
            className="object-cover transition-transform duration-500 group-hover:scale-105 opacity-90"
            unoptimized
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-[var(--text-3)]">
            <Video className="w-8 h-8" />
          </div>
        )}

        {/* Scene Sequence Badge */}
        <div className="absolute top-2.5 left-2.5 z-10 flex items-center gap-1.5 px-2.5 py-1 bg-[rgba(3,5,7,0.8)] backdrop-blur-md border border-[var(--border-1)] rounded-lg text-xs font-mono text-[var(--gold-2)] font-bold">
          <span>Shot #{scene.order}</span>
        </div>

        {/* Status Pill */}
        <div className="absolute top-2.5 right-2.5 z-10">
          {scene.status === "completed" && (
            <span className="badge badge-success flex items-center gap-1">
              <CheckCircle2 className="w-3 h-3" />
              Completed
            </span>
          )}
          {scene.status === "generating" && (
            <span className="badge badge-gold flex items-center gap-1">
              <Loader2 className="w-3 h-3 animate-spin" />
              Generating
            </span>
          )}
          {scene.status === "pending" && (
            <span className="badge bg-[var(--bg-card)] border border-[var(--border-1)] text-[var(--text-3)]">
              Waiting
            </span>
          )}
          {scene.status === "failed" && (
            <span className="badge badge-error flex items-center gap-1">
              <AlertTriangle className="w-3 h-3" />
              Failed
            </span>
          )}
          {scene.status === "paused" && (
            <span className="badge bg-amber-950/70 border border-amber-500/30 text-amber-200 flex items-center gap-1">
              <AlertTriangle className="w-3 h-3" />
              Quota paused
            </span>
          )}
          {scene.status === "paused" && (
            <div className="mt-2 p-2 bg-amber-950/40 border border-amber-500/30 rounded-lg text-xs text-amber-200">
              <p className="font-semibold">Provider quota paused</p>
              <p className="mt-1 text-amber-100/80">
                Wait for the provider quota window to reset, then retry this scene.
              </p>
              {scene.last_error && <p className="mt-1 line-clamp-2">{scene.last_error}</p>}
            </div>
          )}
        </div>

        {/* Play Overlay Button for Completed Clips */}
        {scene.status === "completed" && scene.clip && (
          <button
            onClick={() => onPreview(scene)}
            className="absolute inset-0 z-20 flex items-center justify-center bg-[rgba(3,5,7,0.4)] opacity-0 group-hover:opacity-100 backdrop-blur-xs transition-opacity duration-200"
          >
            <div className="p-3.5 btn-gold text-[#080a0d] rounded-full shadow-xl transform group-hover:scale-110 transition-transform">
              <Play className="w-6 h-6 fill-current translate-x-0.5" />
            </div>
          </button>
        )}
      </div>

      {/* Card Content & Action Controls */}
      <div className="p-4 flex-1 flex flex-col justify-between space-y-3 bg-[var(--bg-card)]">
        <div>
          <div className="flex items-center justify-between">
            <h4 className="font-semibold text-[var(--text-1)] text-sm">{scene.label}</h4>
            <span className="text-[10px] font-mono text-[var(--text-3)] capitalize">{scene.scene_type.replace(/_/g, " ")}</span>
          </div>

          {scene.camera_motion && (
            <div className="mt-1 flex items-center gap-1 text-xs text-[var(--gold-2)] font-medium">
              <Video className="w-3.5 h-3.5" />
              <span>{scene.camera_motion.replace(/_/g, " ")}</span>
            </div>
          )}

          {/* Failure reason */}
          {scene.status === "failed" && scene.last_error && (
            <div className="mt-2 p-2 bg-red-950/40 border border-red-500/30 rounded-lg text-xs text-red-300">
              <p className="line-clamp-2">{scene.last_error}</p>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="pt-2.5 border-t border-[var(--border-1)] flex items-center justify-between text-xs">
          {scene.status === "completed" && scene.clip ? (
            <>
              <div className="text-[var(--text-3)] font-mono text-xs">
                {scene.clip.duration_seconds.toFixed(1)}s • {scene.clip.width}p
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => onPreview(scene)}
                  className="btn-gold px-3 py-1 rounded-lg text-xs font-bold inline-flex items-center gap-1 shadow-sm"
                >
                  <Play className="w-3 h-3 fill-current" />
                  Preview
                </button>
                <div className="relative">
                  <button
                    onClick={() => setShowMotionMenu(!showMotionMenu)}
                    className="p-1.5 btn-ghost rounded-lg transition"
                    title="Regenerate clip"
                  >
                    <RefreshCw className="w-3.5 h-3.5 text-[var(--gold-2)]" />
                  </button>

                  {/* Dropdown Menu for Motion Overrides */}
                  {showMotionMenu && (
                    <div className="absolute right-0 bottom-9 z-30 w-48 glass-gold rounded-xl shadow-2xl p-1.5 space-y-1 border border-[var(--border-2)]">
                      <div className="px-2 py-1 text-[10px] font-bold text-[var(--gold-1)] uppercase">Regenerate with:</div>
                      {MOTION_OPTIONS.map((opt) => (
                        <button
                          key={opt.value}
                          onClick={() => handleRegenSelect(opt.value)}
                          className="w-full text-left px-2.5 py-1.5 rounded-lg text-xs text-[var(--text-2)] hover:text-white hover:bg-[var(--gold-dim)] transition"
                        >
                          {opt.label}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </>
          ) : scene.status === "failed" || scene.status === "paused" ? (
            <>
              <span className={scene.status === "paused" ? "text-amber-200 text-xs" : "text-[var(--text-3)] text-xs"}>
                {scene.status === "paused" ? "Retry after quota reset" : "Ready to retry"}
              </span>
              <button
                onClick={handleRetryClick}
                disabled={isRetrying}
                className={`px-3 py-1 rounded-lg text-xs font-semibold transition flex items-center gap-1 ${
                  scene.status === "paused"
                    ? "bg-amber-950/80 hover:bg-amber-900 text-amber-200 border border-amber-500/30"
                    : "bg-red-950/80 hover:bg-red-900 text-red-200 border border-red-500/30"
                }`}
              >
                {isRetrying ? (
                  <>
                    <Loader2 className="w-3 h-3 animate-spin" />
                    Retrying…
                  </>
                ) : (
                  "Retry"
                )}
              </button>
            </>
          ) : scene.status === "generating" ? (
            <div className="w-full flex items-center justify-between text-[var(--gold-2)] font-mono text-xs">
              <span className="animate-pulse flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5" />
                Synthesizing video…
              </span>
              <span>Veo 3.1</span>
            </div>
          ) : (
            <div className="text-[var(--text-3)] text-xs font-mono">
              Ready for batch generation
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
