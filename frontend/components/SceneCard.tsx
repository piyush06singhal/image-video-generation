"use client";

import React, { useState } from "react";
import { ImageMetadata } from "@/types/image";
import {
  SCENE_TYPE_LABELS,
  LIGHTING_LABELS,
  CAMERA_VIEW_LABELS,
  SceneType,
} from "@/types/scene";
import { QualityBadge } from "./QualityBadge";
import {
  CheckCircle2,
  UserCheck,
  RefreshCw,
  Sun,
  Camera,
  DoorOpen,
  Tag,
  AlertTriangle,
  Loader2,
  Maximize2,
  Sparkles,
} from "lucide-react";

interface SceneCardProps {
  image: ImageMetadata;
  onUpdateScene: (imageId: string, newSceneType: SceneType) => Promise<void>;
  onReanalyzeImage: (imageId: string) => Promise<void>;
  onInspectImage: (image: ImageMetadata) => void;
  isAnalyzing: boolean;
}

export const SceneCard: React.FC<SceneCardProps> = ({
  image,
  onUpdateScene,
  onReanalyzeImage,
  onInspectImage,
  isAnalyzing,
}) => {
  const [isUpdating, setIsUpdating] = useState(false);
  const scene = image.scene;
  const quality = image.quality;
  const isCompleted = image.analysis_status === "completed" && !!scene;
  const isFailed = image.analysis_status === "failed";
  const isProcessing = image.analysis_status === "processing";

  const handleSceneChange = async (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newType = e.target.value as SceneType;
    setIsUpdating(true);
    try {
      await onUpdateScene(image.id, newType);
    } finally {
      setIsUpdating(false);
    }
  };

  const previewSrc =
    image.thumbnail_url || image.file_url || `/api/projects/${image.id}/thumbnail`;

  return (
    <div
      className={`glass-gold rounded-2xl overflow-hidden flex flex-col card-hover transition-all duration-300 ${
        isFailed
          ? "border-red-500/40"
          : isCompleted && scene?.user_corrected
          ? "border-[var(--gold-2)]"
          : "border-[var(--border-1)]"
      }`}
    >
      {/* Top Image Preview */}
      <div className="relative aspect-video bg-[var(--bg-0)] overflow-hidden group">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={previewSrc}
          alt={image.original_filename}
          className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
          loading="lazy"
        />

        {/* Action Overlay */}
        <div className="absolute inset-0 bg-[rgba(3,5,7,0.7)] backdrop-blur-xs opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2.5 p-3">
          <button
            type="button"
            onClick={() => onInspectImage(image)}
            className="btn-gold px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 shadow-md"
            title="Inspect full image and scene metadata"
          >
            <Maximize2 className="w-3.5 h-3.5" />
            <span>Inspect</span>
          </button>

          <button
            type="button"
            onClick={() => onReanalyzeImage(image.id)}
            disabled={isAnalyzing || isUpdating}
            className="btn-outline-gold px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 disabled:opacity-50"
            title="Re-analyze this image with AI"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isProcessing ? "animate-spin" : ""}`} />
            <span>Re-analyze</span>
          </button>
        </div>

        {/* Top Floating Badges */}
        <div className="absolute top-2.5 left-2.5 z-10">
          <QualityBadge quality={quality} />
        </div>

        <div className="absolute top-2.5 right-2.5 z-10">
          {scene?.user_corrected ? (
            <span className="badge badge-gold">
              <UserCheck className="w-3 h-3" />
              Edited
            </span>
          ) : isCompleted && scene ? (
            <span className="badge badge-success">
              <CheckCircle2 className="w-3 h-3" />
              {(scene.confidence * 100).toFixed(0)}% Conf
            </span>
          ) : null}
        </div>
      </div>

      {/* Card Body & Scene Controls */}
      <div className="p-4 flex flex-col justify-between grow space-y-3.5 bg-[var(--bg-card)]">
        {/* Filename & Classification Selector */}
        <div>
          <div className="flex items-center justify-between text-xs text-[var(--text-2)] mb-2">
            <span className="truncate max-w-[170px] font-semibold text-[var(--text-1)]" title={image.original_filename}>
              {image.original_filename}
            </span>
            <span className="font-mono text-[10px] text-[var(--text-3)] bg-[var(--bg-0)] px-2 py-0.5 rounded border border-[var(--border-1)]">
              {image.width}×{image.height}
            </span>
          </div>

          {/* Room / Scene Type Dropdown */}
          <div className="space-y-1.5">
            <label
              htmlFor={`scene-select-${image.id}`}
              className="block text-[10px] font-bold text-[var(--gold-1)] uppercase tracking-wider flex items-center justify-between"
            >
              <span>Scene Classification</span>
              {scene && (
                <span className="text-[10px] text-[var(--gold-3)] font-mono lowercase">
                  {scene.scene_type}
                </span>
              )}
            </label>
            <div className="relative">
              <select
                id={`scene-select-${image.id}`}
                value={scene?.scene_type || "unknown"}
                onChange={handleSceneChange}
                disabled={isAnalyzing || isUpdating}
                className="w-full rounded-xl px-3 py-2 text-xs font-semibold focus:outline-none transition-colors cursor-pointer disabled:opacity-60"
              >
                {Object.entries(SCENE_TYPE_LABELS).map(([key, label]) => (
                  <option key={key} value={key}>
                    {label}
                  </option>
                ))}
              </select>
              {isUpdating && (
                <div className="absolute right-3 top-2.5">
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-[var(--gold-2)]" />
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Failed State Alert */}
        {isFailed && (
          <div className="p-3 bg-red-950/40 border border-red-500/30 rounded-xl text-xs text-red-300 space-y-1.5">
            <div className="flex items-center gap-1.5 font-semibold text-red-200">
              <AlertTriangle className="w-3.5 h-3.5 text-red-400" />
              <span>Analysis Failed</span>
            </div>
            <p className="line-clamp-2 text-red-300/90 text-[11px] leading-relaxed">
              {image.analysis_error || "Could not complete visual inspection."}
            </p>
            <button
              type="button"
              onClick={() => onReanalyzeImage(image.id)}
              disabled={isAnalyzing}
              className="text-xs text-red-200 font-semibold underline underline-offset-2 hover:text-white transition-colors"
            >
              Retry analysis
            </button>
          </div>
        )}

        {/* Completed Scene Details */}
        {isCompleted && scene && (
          <div className="space-y-2.5 text-xs">
            {/* Description */}
            <p className="text-[var(--text-2)] leading-relaxed text-xs bg-[var(--bg-0)] p-2.5 rounded-xl border border-[var(--border-1)]">
              {scene.description}
            </p>

            {/* Feature Chips */}
            {scene.features && scene.features.length > 0 && (
              <div className="flex items-center gap-1.5 flex-wrap">
                <Tag className="w-3 h-3 text-[var(--gold-1)] shrink-0" />
                {scene.features.slice(0, 4).map((f, i) => (
                  <span
                    key={i}
                    className="text-[10px] bg-[var(--gold-dim)] text-[var(--gold-3)] px-2 py-0.5 rounded-md border border-[var(--border-1)]"
                  >
                    {f}
                  </span>
                ))}
                {scene.features.length > 4 && (
                  <span className="text-[10px] text-[var(--text-3)] font-mono">
                    +{scene.features.length - 4}
                  </span>
                )}
              </div>
            )}

            {/* Environmental & Perspective Badges */}
            <div className="grid grid-cols-2 gap-1.5 pt-0.5 text-xs">
              <div className="flex items-center gap-1 truncate bg-[var(--bg-0)] px-2 py-1 rounded-lg border border-[var(--border-1)] text-[var(--text-2)]">
                <Sun className="w-3 h-3 text-[var(--gold-2)] shrink-0" />
                <span className="truncate">{LIGHTING_LABELS[scene.lighting] || scene.lighting}</span>
              </div>
              <div className="flex items-center gap-1 truncate bg-[var(--bg-0)] px-2 py-1 rounded-lg border border-[var(--border-1)] text-[var(--text-2)]">
                <Camera className="w-3 h-3 text-[var(--gold-1)] shrink-0" />
                <span className="truncate">{CAMERA_VIEW_LABELS[scene.camera_view] || scene.camera_view}</span>
              </div>
            </div>

            {/* Visible Passages */}
            {scene.visible_connections && scene.visible_connections.length > 0 && (
              <div className="flex items-start gap-1.5 text-xs text-emerald-300 bg-emerald-950/30 px-2.5 py-1.5 rounded-lg border border-emerald-500/20">
                <DoorOpen className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                <span className="truncate font-medium">
                  {scene.visible_connections.join(", ")}
                </span>
              </div>
            )}
          </div>
        )}

        {/* Pending Analysis Placeholder */}
        {!isCompleted && !isFailed && !isProcessing && (
          <div className="p-3.5 text-center text-xs text-[var(--text-3)] bg-[var(--bg-0)] rounded-xl border border-dashed border-[var(--border-1)] flex items-center justify-center gap-2">
            <Sparkles className="w-3.5 h-3.5 text-[var(--gold-2)]" />
            <span>Pending visual analysis</span>
          </div>
        )}

        {/* Processing Spinner */}
        {isProcessing && (
          <div className="p-3.5 text-center text-xs text-[var(--gold-2)] bg-[var(--gold-dim)] rounded-xl border border-[var(--border-2)] flex items-center justify-center gap-2">
            <Loader2 className="w-4 h-4 animate-spin text-[var(--gold-1)]" />
            <span>Analyzing scene with AI…</span>
          </div>
        )}
      </div>
    </div>
  );
};
