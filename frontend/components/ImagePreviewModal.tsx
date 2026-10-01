"use client";

import React from "react";
import {
  X,
  ShieldCheck,
  Brain,
  Sun,
  Camera,
  DoorOpen,
  Tag,
  UserCheck,
  Layers,
  Sparkles,
} from "lucide-react";
import { ImageMetadata, StagedImage } from "@/types/image";
import {
  SCENE_TYPE_LABELS,
  LIGHTING_LABELS,
  CAMERA_VIEW_LABELS,
} from "@/types/scene";
import { formatAspectRatio, formatFileSize } from "@/lib/utils";

interface ImagePreviewModalProps {
  image: ImageMetadata | StagedImage | null;
  onClose: () => void;
}

export const ImagePreviewModal: React.FC<ImagePreviewModalProps> = ({
  image,
  onClose,
}) => {
  if (!image) return null;

  // Normalize image data from either StagedImage or ImageMetadata
  const isStaged = "name" in image;
  const staged = isStaged ? (image as StagedImage) : null;
  const meta = isStaged ? staged?.serverData : (image as ImageMetadata);

  const name = isStaged ? staged!.name : meta?.original_filename || "Image";
  const size = isStaged ? staged!.size : meta?.file_size || 0;
  const width = isStaged ? staged!.width : meta?.width;
  const height = isStaged ? staged!.height : meta?.height;
  const aspectRatio = isStaged ? staged!.aspectRatio : meta?.aspect_ratio;
  const previewUrl =
    staged?.previewUrl ||
    meta?.file_url ||
    meta?.thumbnail_url ||
    "";

  const scene = meta?.scene;
  const quality = meta?.quality;
  const sha256 = meta?.sha256;

  return (
    <div
      className="fixed inset-0 z-50 modal-backdrop flex items-center justify-center p-4 sm:p-6 animate-in fade-in duration-200"
      onClick={onClose}
    >
      <div
        className="glass-card-elevated rounded-3xl max-w-5xl w-full max-h-[92vh] overflow-hidden shadow-2xl flex flex-col border border-slate-700/60"
        style={{ background: "rgba(13, 17, 23, 0.95)" }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="px-6 py-4.5 border-b border-slate-800 flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2.5 flex-wrap">
              <h3 className="text-base font-semibold text-slate-100 truncate max-w-md sm:max-w-xl">
                {name}
              </h3>
              {scene?.scene_type && (
                <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-indigo-950 text-indigo-300 border border-indigo-500/30">
                  {SCENE_TYPE_LABELS[scene.scene_type] || scene.scene_type}
                </span>
              )}
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Visual Scene Inspection &amp; Analytical Metadata
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800/80 transition-colors border border-transparent hover:border-slate-700"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Main Image View */}
          <div className="lg:col-span-7 bg-slate-950 rounded-2xl overflow-hidden flex items-center justify-center min-h-[320px] max-h-[520px] border border-slate-800/80 shadow-inner">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={previewUrl}
              alt={name}
              className="max-h-[500px] w-auto max-w-full object-contain"
            />
          </div>

          {/* Metadata & Scene Sidebar */}
          <div className="lg:col-span-5 space-y-4 text-xs">
            {/* Scene Understanding Card */}
            {scene && (
              <div className="glass-card p-4.5 rounded-2xl border border-slate-800 space-y-3 bg-slate-900/60">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 font-semibold text-slate-200 uppercase tracking-wider text-[11px]">
                    <Brain className="w-4 h-4 text-indigo-400" />
                    <span>Visual Scene Metadata</span>
                  </div>
                  {scene.user_corrected ? (
                    <span className="flex items-center gap-1 text-[10.5px] font-semibold text-indigo-300 bg-indigo-950/80 px-2.5 py-0.5 rounded-full border border-indigo-500/30">
                      <UserCheck className="w-3 h-3" />
                      Confirmed
                    </span>
                  ) : (
                    <span className="text-[10.5px] font-mono text-emerald-400 bg-emerald-950/60 px-2.5 py-0.5 rounded-full border border-emerald-500/30">
                      {(scene.confidence * 100).toFixed(0)}% Confidence
                    </span>
                  )}
                </div>

                <p className="text-slate-300 leading-relaxed bg-slate-950/60 p-3 rounded-xl border border-slate-800/80 text-[11.5px]">
                  {scene.description}
                </p>

                {scene.features && scene.features.length > 0 && (
                  <div>
                    <span className="text-slate-400 block mb-1.5 font-medium">
                      Identified Features:
                    </span>
                    <div className="flex items-center gap-1.5 flex-wrap">
                      {scene.features.map((f, i) => (
                        <span
                          key={i}
                          className="bg-slate-800/80 border border-slate-700/60 text-slate-300 px-2.5 py-0.5 rounded-lg text-[11px]"
                        >
                          {f}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                <div className="grid grid-cols-2 gap-2 pt-1">
                  <div className="bg-slate-950/60 p-2.5 rounded-xl border border-slate-800/80">
                    <span className="text-slate-500 block text-[10px]">Lighting:</span>
                    <span className="font-medium text-slate-200 flex items-center gap-1.5 mt-0.5">
                      <Sun className="w-3.5 h-3.5 text-amber-400" />
                      {LIGHTING_LABELS[scene.lighting] || scene.lighting}
                    </span>
                  </div>
                  <div className="bg-slate-950/60 p-2.5 rounded-xl border border-slate-800/80">
                    <span className="text-slate-500 block text-[10px]">Camera View:</span>
                    <span className="font-medium text-slate-200 flex items-center gap-1.5 mt-0.5">
                      <Camera className="w-3.5 h-3.5 text-indigo-400" />
                      {CAMERA_VIEW_LABELS[scene.camera_view] || scene.camera_view}
                    </span>
                  </div>
                </div>

                {scene.visible_connections && scene.visible_connections.length > 0 && (
                  <div className="bg-emerald-950/40 p-3 rounded-xl border border-emerald-500/25 text-emerald-300 text-[11px] flex items-start gap-2">
                    <DoorOpen className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                    <div>
                      <strong className="text-emerald-200">Visible Passages:</strong>{" "}
                      {scene.visible_connections.join(", ")}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Quality Analysis Card */}
            {quality && (
              <div className="glass-card p-4.5 rounded-2xl border border-slate-800 space-y-2 bg-slate-900/60">
                <div className="flex items-center justify-between font-semibold text-slate-200 text-[11px] uppercase tracking-wider">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-indigo-400" />
                    <span>Quality Signals</span>
                  </div>
                  <span
                    className={`capitalize font-bold text-xs ${
                      quality.status === "good"
                        ? "text-emerald-400"
                        : quality.status === "acceptable"
                        ? "text-amber-400"
                        : "text-rose-400"
                    }`}
                  >
                    {quality.status}
                  </span>
                </div>

                <div className="grid grid-cols-3 gap-2 text-center pt-1.5">
                  <div className="bg-slate-950/60 p-2 rounded-xl border border-slate-800/80">
                    <span className="text-[10px] text-slate-500 block">Sharpness</span>
                    <span className="font-mono font-semibold text-emerald-400 text-xs">
                      {(quality.sharpness_score * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="bg-slate-950/60 p-2 rounded-xl border border-slate-800/80">
                    <span className="text-[10px] text-slate-500 block">Brightness</span>
                    <span className="font-mono font-semibold text-amber-300 text-xs">
                      {(quality.brightness_score * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="bg-slate-950/60 p-2 rounded-xl border border-slate-800/80">
                    <span className="text-[10px] text-slate-500 block">Contrast</span>
                    <span className="font-mono font-semibold text-indigo-300 text-xs">
                      {(quality.contrast_score * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* Technical Metadata */}
            <div className="glass-card p-4 rounded-2xl border border-slate-800 space-y-2 text-[11px] bg-slate-900/60">
              <div className="flex justify-between">
                <span className="text-slate-400">Dimensions:</span>
                <span className="font-medium text-slate-200 font-mono">
                  {width} × {height} px ({formatAspectRatio(aspectRatio || 1)})
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">File Size:</span>
                <span className="font-mono text-slate-200">{formatFileSize(size)}</span>
              </div>
              {sha256 && (
                <div className="pt-1">
                  <span className="text-slate-500 block mb-1">SHA-256 Checksum:</span>
                  <span className="font-mono text-[9.5px] text-slate-400 bg-slate-950 p-2 rounded-xl border border-slate-800 block break-all">
                    {sha256}
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
