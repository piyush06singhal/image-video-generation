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
      className={`glass-card image-card-hover rounded-2xl overflow-hidden flex flex-col transition-all duration-300 ${
        isFailed
          ? "border-rose-500/40 ring-1 ring-rose-500/20 shadow-[0_0_20px_rgba(244,63,94,0.15)]"
          : isCompleted && scene?.user_corrected
          ? "border-indigo-500/40 ring-1 ring-indigo-500/20 shadow-[0_0_20px_rgba(99,102,241,0.15)]"
          : "border-slate-800/80 hover:border-slate-700"
      }`}
      style={{ background: "rgba(17, 24, 39, 0.75)" }}
    >
      {/* Top Image Preview */}
      <div className="relative aspect-4/3 bg-slate-950 overflow-hidden group">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={previewSrc}
          alt={image.original_filename}
          className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
          loading="lazy"
        />

        {/* Action Overlay */}
        <div className="absolute inset-0 bg-slate-950/70 backdrop-blur-xs opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2.5 p-3">
          <button
            type="button"
            onClick={() => onInspectImage(image)}
            className="px-3 py-1.5 bg-slate-800/90 hover:bg-slate-700 text-white rounded-lg shadow-lg hover:scale-105 transition-all text-xs flex items-center gap-1.5 font-medium border border-slate-600/50"
            title="Inspect full image and scene metadata"
          >
            <Maximize2 className="w-3.5 h-3.5 text-indigo-400" />
            <span>Inspect</span>
          </button>

          <button
            type="button"
            onClick={() => onReanalyzeImage(image.id)}
            disabled={isAnalyzing || isUpdating}
            className="px-3 py-1.5 bg-indigo-600/90 hover:bg-indigo-500 text-white rounded-lg shadow-lg hover:scale-105 transition-all text-xs flex items-center gap-1.5 font-medium disabled:opacity-50 border border-indigo-400/30"
            title="Re-analyze this image with AI"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isProcessing ? "animate-spin" : ""}`} />
            <span>Re-analyze</span>
          </button>
        </div>

        {/* Top Floating Badges */}
        <div className="absolute top-2.5 left-2.5">
          <QualityBadge quality={quality} />
        </div>

        <div className="absolute top-2.5 right-2.5">
          {scene?.user_corrected ? (
            <span className="flex items-center gap-1 text-[10px] font-semibold bg-indigo-500/90 text-white backdrop-blur-md px-2.5 py-0.5 rounded-full shadow-md border border-indigo-400/30">
              <UserCheck className="w-3 h-3" />
              Confirmed
            </span>
          ) : isCompleted && scene ? (
            <span className="flex items-center gap-1 text-[10px] font-mono font-medium bg-slate-900/90 text-emerald-400 backdrop-blur-md px-2.5 py-0.5 rounded-full shadow-md border border-emerald-500/30">
              <CheckCircle2 className="w-3 h-3 text-emerald-400" />
              {(scene.confidence * 100).toFixed(0)}% Conf
            </span>
          ) : null}
        </div>
      </div>

      {/* Card Body & Scene Controls */}
      <div className="p-4 flex flex-col justify-between grow space-y-3.5">
        {/* Filename & Classification Selector */}
        <div>
          <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
            <span className="truncate max-w-[170px] font-medium text-slate-300" title={image.original_filename}>
              {image.original_filename}
            </span>
            <span className="font-mono text-[10.5px] text-slate-500 bg-slate-800/60 px-1.5 py-0.5 rounded border border-slate-700/40">
              {image.width}×{image.height}
            </span>
          </div>

          {/* Room / Scene Type Dropdown */}
          <div className="space-y-1.5">
            <label
              htmlFor={`scene-select-${image.id}`}
              className="block text-[10px] font-semibold text-slate-400 uppercase tracking-wider flex items-center justify-between"
            >
              <span>Scene Classification</span>
              {scene && (
                <span className="text-[9.5px] text-indigo-400 font-mono lowercase tracking-normal">
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
                className="w-full bg-slate-900/80 border border-slate-700/80 hover:border-slate-600 rounded-xl px-3 py-2 text-xs font-medium text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-500 transition-colors cursor-pointer disabled:opacity-60"
              >
                {Object.entries(SCENE_TYPE_LABELS).map(([key, label]) => (
                  <option key={key} value={key} className="bg-slate-900 text-slate-100">
                    {label}
                  </option>
                ))}
              </select>
              {isUpdating && (
                <div className="absolute right-3 top-2.5">
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-indigo-400" />
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Failed State Alert */}
        {isFailed && (
          <div className="p-3 bg-rose-950/40 border border-rose-500/30 rounded-xl text-[11px] text-rose-300 space-y-1.5">
            <div className="flex items-center gap-1.5 font-semibold text-rose-200">
              <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />
              <span>Analysis Failed</span>
            </div>
            <p className="line-clamp-2 text-rose-300/90 leading-relaxed">
              {image.analysis_error || "Could not complete visual inspection."}
            </p>
            <button
              type="button"
              onClick={() => onReanalyzeImage(image.id)}
              disabled={isAnalyzing}
              className="text-xs text-rose-200 font-semibold underline underline-offset-2 hover:text-white transition-colors"
            >
              Retry analysis
            </button>
          </div>
        )}

        {/* Completed Scene Details */}
        {isCompleted && scene && (
          <div className="space-y-2.5 text-xs">
            {/* Description */}
            <p className="text-slate-300 leading-relaxed text-[11.5px] bg-slate-900/60 p-2.5 rounded-xl border border-slate-800/80">
              {scene.description}
            </p>

            {/* Feature Chips */}
            {scene.features && scene.features.length > 0 && (
              <div className="flex items-center gap-1.5 flex-wrap">
                <Tag className="w-3 h-3 text-slate-500 shrink-0" />
                {scene.features.slice(0, 4).map((f, i) => (
                  <span
                    key={i}
                    className="text-[10px] bg-slate-800/80 text-slate-300 px-2 py-0.5 rounded-md border border-slate-700/60"
                  >
                    {f}
                  </span>
                ))}
                {scene.features.length > 4 && (
                  <span className="text-[9.5px] text-slate-500 font-mono">
                    +{scene.features.length - 4}
                  </span>
                )}
              </div>
            )}

            {/* Environmental & Perspective Badges */}
            <div className="grid grid-cols-2 gap-1.5 pt-0.5 text-[10.5px]">
              <div className="flex items-center gap-1 truncate bg-slate-900/60 px-2 py-1 rounded-lg border border-slate-800/80 text-slate-300">
                <Sun className="w-3 h-3 text-amber-400 shrink-0" />
                <span className="truncate">{LIGHTING_LABELS[scene.lighting] || scene.lighting}</span>
              </div>
              <div className="flex items-center gap-1 truncate bg-slate-900/60 px-2 py-1 rounded-lg border border-slate-800/80 text-slate-300">
                <Camera className="w-3 h-3 text-indigo-400 shrink-0" />
                <span className="truncate">{CAMERA_VIEW_LABELS[scene.camera_view] || scene.camera_view}</span>
              </div>
            </div>

            {/* Visible Passages */}
            {scene.visible_connections && scene.visible_connections.length > 0 && (
              <div className="flex items-start gap-1.5 text-[10.5px] text-emerald-300 bg-emerald-950/40 px-2.5 py-1.5 rounded-lg border border-emerald-500/25">
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
          <div className="p-3.5 text-center text-xs text-slate-500 bg-slate-900/40 rounded-xl border border-dashed border-slate-800 flex items-center justify-center gap-2">
            <Sparkles className="w-3.5 h-3.5 text-slate-600" />
            <span>Pending visual analysis</span>
          </div>
        )}

        {/* Processing Spinner */}
        {isProcessing && (
          <div className="p-3.5 text-center text-xs text-indigo-300 bg-indigo-950/40 rounded-xl border border-indigo-500/30 flex items-center justify-center gap-2">
            <Loader2 className="w-4 h-4 animate-spin text-indigo-400" />
            <span>Analyzing visual scene...</span>
          </div>
        )}
      </div>
    </div>
  );
};
