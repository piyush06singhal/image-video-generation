"use client";

import React from "react";
import { VideoClipMetadata } from "@/types/generation";
import { X, CheckCircle2, Video, Clock, Monitor, Sparkles } from "lucide-react";

interface VideoPlayerModalProps {
  isOpen: boolean;
  sceneLabel: string;
  clip: VideoClipMetadata | null;
  onClose: () => void;
}

export function VideoPlayerModal({
  isOpen,
  sceneLabel,
  clip,
  onClose,
}: VideoPlayerModalProps) {
  if (!isOpen || !clip) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 modal-backdrop anim-fade-in"
      onClick={onClose}
    >
      <div
        className="glass-gold relative w-full max-w-4xl rounded-3xl shadow-2xl overflow-hidden flex flex-col border border-[var(--border-2)]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[var(--border-1)] bg-[var(--bg-0)]">
          <div className="flex items-center space-x-3">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
            <h3 className="text-base font-bold font-display text-[var(--text-1)]">
              {sceneLabel} — Generated Walkthrough Clip
            </h3>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-[var(--text-3)] hover:text-white rounded-xl bg-[var(--bg-card)] hover:bg-[var(--gold-dim)] transition border border-transparent hover:border-[var(--border-1)]"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Video Player */}
        <div className="relative bg-black flex items-center justify-center aspect-video w-full">
          <video
            src={clip.clip_url}
            controls
            autoPlay
            loop
            playsInline
            className="w-full h-full max-h-[60vh] object-contain"
          />
        </div>

        {/* Video Metadata & Prompt Details */}
        <div className="p-6 bg-[var(--bg-card)] border-t border-[var(--border-1)] space-y-4">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            <div className="bg-[var(--bg-0)] border border-[var(--border-1)] p-3 rounded-xl">
              <span className="text-[10px] font-mono text-[var(--gold-1)] block uppercase font-bold flex items-center gap-1">
                <Clock className="w-3 h-3" /> Duration
              </span>
              <span className="text-[var(--text-1)] font-semibold font-mono text-sm mt-0.5 block">
                {clip.duration_seconds.toFixed(1)}s
              </span>
            </div>
            <div className="bg-[var(--bg-0)] border border-[var(--border-1)] p-3 rounded-xl">
              <span className="text-[10px] font-mono text-[var(--gold-1)] block uppercase font-bold flex items-center gap-1">
                <Monitor className="w-3 h-3" /> Resolution
              </span>
              <span className="text-[var(--text-1)] font-semibold font-mono text-sm mt-0.5 block">
                {clip.width} × {clip.height}
              </span>
            </div>
            <div className="bg-[var(--bg-0)] border border-[var(--border-1)] p-3 rounded-xl">
              <span className="text-[10px] font-mono text-[var(--gold-1)] block uppercase font-bold flex items-center gap-1">
                <Video className="w-3 h-3" /> Camera Motion
              </span>
              <span className="text-[var(--gold-2)] font-medium capitalize text-xs mt-0.5 block">
                {clip.camera_motion.replace(/_/g, " ")}
              </span>
            </div>
            <div className="bg-[var(--bg-0)] border border-[var(--border-1)] p-3 rounded-xl">
              <span className="text-[10px] font-mono text-[var(--gold-1)] block uppercase font-bold flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3 text-emerald-400" /> Quality Check
              </span>
              <span className="text-emerald-400 font-medium capitalize text-xs mt-0.5 block">
                {clip.quality.replace(/_/g, " ")}
              </span>
            </div>
          </div>

          <div className="bg-[var(--bg-0)] border border-[var(--border-1)] p-3.5 rounded-xl">
            <span className="text-[10px] font-mono uppercase text-[var(--gold-1)] font-bold block mb-1 flex items-center gap-1">
              <Sparkles className="w-3 h-3" /> Applied Generation Prompt
            </span>
            <p className="text-xs text-[var(--text-2)] leading-relaxed italic">
              &ldquo;{clip.prompt}&rdquo;
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
