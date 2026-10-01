"use client";

import React from "react";
import {
  X,
  ShieldCheck,
  Brain,
  Sun,
  Camera,
  DoorOpen,
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

  // Normalize image data
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
      className="fixed inset-0 z-50 modal-backdrop flex items-center justify-center p-4 sm:p-6 anim-fade-in"
      onClick={onClose}
    >
      <div
        className="glass-gold rounded-3xl max-w-5xl w-full max-h-[92vh] overflow-hidden shadow-2xl flex flex-col border border-[var(--border-2)]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="px-6 py-4.5 border-b border-[var(--border-1)] flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2.5 flex-wrap">
              <h3 className="text-base font-bold font-display text-[var(--text-1)] truncate max-w-md sm:max-w-xl">
                {name}
              </h3>
              {scene?.scene_type && (
                <span className="badge badge-gold">
                  {SCENE_TYPE_LABELS[scene.scene_type] || scene.scene_type}
                </span>
              )}
            </div>
            <p className="text-xs text-[var(--text-3)] mt-0.5">
              Visual Scene Inspection &amp; Analytical Metadata
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-2 rounded-xl text-[var(--text-2)] hover:text-white hover:bg-[var(--gold-dim)] transition-colors border border-transparent hover:border-[var(--border-2)]"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Main Image View */}
          <div className="lg:col-span-7 bg-[var(--bg-0)] rounded-2xl overflow-hidden flex items-center justify-center min-h-[320px] max-h-[520px] border border-[var(--border-1)] shadow-inner">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={previewUrl}
              alt={name}
              className="max-h-[500px] w-auto max-w-full object-contain"
            />
          </div>

          {/* Metadata Sidebar */}
          <div className="lg:col-span-5 space-y-4">
            {/* Quality Section */}
            {quality && (
              <div className="bg-[var(--bg-card)] p-4 rounded-2xl border border-[var(--border-1)] space-y-2.5">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-[var(--gold-1)] flex items-center gap-1.5 uppercase tracking-wider">
                    <ShieldCheck className="w-4 h-4 text-[var(--gold-2)]" />
                    Quality Inspection
                  </span>
                  <span className="badge badge-success text-[10px]">
                    {quality.status}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="bg-[var(--bg-0)] p-2 rounded-xl border border-[var(--border-1)]">
                    <span className="text-[10px] text-[var(--text-3)] block">Sharpness</span>
                    <span className="font-mono text-emerald-400 font-medium">
                      {(quality.sharpness_score * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="bg-[var(--bg-0)] p-2 rounded-xl border border-[var(--border-1)]">
                    <span className="text-[10px] text-[var(--text-3)] block">Brightness</span>
                    <span className="font-mono text-[var(--gold-2)] font-medium">
                      {(quality.brightness_score * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="bg-[var(--bg-0)] p-2 rounded-xl border border-[var(--border-1)]">
                    <span className="text-[10px] text-[var(--text-3)] block">Contrast</span>
                    <span className="font-mono text-[var(--text-1)] font-medium">
                      {(quality.contrast_score * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="bg-[var(--bg-0)] p-2 rounded-xl border border-[var(--border-1)]">
                    <span className="text-[10px] text-[var(--text-3)] block">Dimensions</span>
                    <span className="font-mono text-[var(--text-1)] font-medium">
                      {width} × {height}
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* Scene Understanding Section */}
            {scene && (
              <div className="bg-[var(--bg-card)] p-4 rounded-2xl border border-[var(--border-1)] space-y-2.5">
                <span className="text-xs font-bold text-[var(--gold-1)] flex items-center gap-1.5 uppercase tracking-wider">
                  <Brain className="w-4 h-4 text-[var(--gold-2)]" />
                  Multimodal Scene Intelligence
                </span>

                <p className="text-xs text-[var(--text-2)] bg-[var(--bg-0)] p-3 rounded-xl border border-[var(--border-1)] leading-relaxed">
                  {scene.description}
                </p>

                {scene.features && scene.features.length > 0 && (
                  <div className="space-y-1">
                    <span className="text-[10px] font-bold text-[var(--text-3)] uppercase tracking-wider block">
                      Recognized Features
                    </span>
                    <div className="flex flex-wrap gap-1.5">
                      {scene.features.map((f, i) => (
                        <span
                          key={i}
                          className="badge badge-gold text-[10px]"
                        >
                          {f}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                <div className="grid grid-cols-2 gap-2 text-xs pt-1">
                  <div className="flex items-center gap-2 bg-[var(--bg-0)] p-2 rounded-xl border border-[var(--border-1)]">
                    <Sun className="w-3.5 h-3.5 text-[var(--gold-2)] shrink-0" />
                    <span className="truncate text-[var(--text-2)] text-xs">
                      {LIGHTING_LABELS[scene.lighting] || scene.lighting}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 bg-[var(--bg-0)] p-2 rounded-xl border border-[var(--border-1)]">
                    <Camera className="w-3.5 h-3.5 text-[var(--gold-1)] shrink-0" />
                    <span className="truncate text-[var(--text-2)] text-xs">
                      {CAMERA_VIEW_LABELS[scene.camera_view] || scene.camera_view}
                    </span>
                  </div>
                </div>

                {scene.visible_connections && scene.visible_connections.length > 0 && (
                  <div className="flex items-center gap-2 text-xs text-emerald-300 bg-emerald-950/30 p-2.5 rounded-xl border border-emerald-500/20">
                    <DoorOpen className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span className="truncate font-medium">
                      Passages to: {scene.visible_connections.join(", ")}
                    </span>
                  </div>
                )}
              </div>
            )}

            {/* Technical Metadata */}
            <div className="bg-[var(--bg-card)] p-4 rounded-2xl border border-[var(--border-1)] text-xs space-y-2">
              <span className="text-[10px] font-bold text-[var(--text-3)] uppercase tracking-wider block">
                File Details
              </span>
              <div className="space-y-1 font-mono text-[11px] text-[var(--text-2)]">
                <div className="flex justify-between">
                  <span className="text-[var(--text-3)]">File Size:</span>
                  <span>{formatFileSize(size)}</span>
                </div>
                {aspectRatio && (
                  <div className="flex justify-between">
                    <span className="text-[var(--text-3)]">Aspect Ratio:</span>
                    <span>{formatAspectRatio(aspectRatio)}</span>
                  </div>
                )}
                {sha256 && (
                  <div className="flex flex-col gap-0.5 pt-1 border-t border-[var(--border-1)]">
                    <span className="text-[var(--text-3)]">SHA256 Fingerprint:</span>
                    <span className="text-[9.5px] truncate text-[var(--text-3)]">
                      {sha256}
                    </span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
