"use client";

import React from "react";
import { ImageCard } from "./ImageCard";
import { StagedImage } from "@/types/image";
import { Trash2, Upload, ArrowRight, Layers, CheckCircle2, AlertTriangle, Clock } from "lucide-react";

interface ImageGridProps {
  images: StagedImage[];
  onRemove: (id: string) => void;
  onClearAll: () => void;
  onUpload: () => void;
  onPreview: (image: StagedImage) => void;
  isUploading: boolean;
  hasUnsavedChanges: boolean;
  onContinueToPhase2: () => void;
}

export const ImageGrid: React.FC<ImageGridProps> = ({
  images,
  onRemove,
  onClearAll,
  onUpload,
  onPreview,
  isUploading,
  hasUnsavedChanges,
  onContinueToPhase2,
}) => {
  if (images.length === 0) return null;

  const validatedCount = images.filter((img) => img.status === "validated").length;
  const errorCount = images.filter((img) => img.status === "error").length;
  const stagedCount = images.filter((img) => img.status === "staged").length;
  const uploadingCount = images.filter((img) => img.status === "uploading").length;

  return (
    <div className="space-y-4 animate-slide-up">
      {/* Toolbar */}
      <div
        className="rounded-2xl p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4"
        style={{
          background: "rgba(22, 32, 50, 0.7)",
          border: "1px solid rgba(148, 163, 184, 0.1)",
          backdropFilter: "blur(12px)",
        }}
      >
        {/* Stats */}
        <div className="flex items-center gap-4">
          <div
            className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0"
            style={{
              background: "rgba(99, 102, 241, 0.12)",
              border: "1px solid rgba(99, 102, 241, 0.18)",
            }}
          >
            <Layers className="w-4.5 h-4.5" style={{ color: "#818cf8" }} />
          </div>

          <div>
            <p className="text-sm font-semibold" style={{ color: "#e2e8f0" }}>
              {images.length} Photograph{images.length !== 1 ? "s" : ""} Selected
            </p>
            <div className="flex items-center gap-3 mt-0.5 text-[11px]">
              {validatedCount > 0 && (
                <span className="flex items-center gap-1" style={{ color: "#34d399" }}>
                  <CheckCircle2 className="w-3 h-3" />
                  {validatedCount} validated
                </span>
              )}
              {stagedCount > 0 && (
                <span className="flex items-center gap-1" style={{ color: "#818cf8" }}>
                  <Clock className="w-3 h-3" />
                  {stagedCount} pending
                </span>
              )}
              {errorCount > 0 && (
                <span className="flex items-center gap-1" style={{ color: "#fb7185" }}>
                  <AlertTriangle className="w-3 h-3" />
                  {errorCount} rejected
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2.5 flex-wrap">
          <button
            type="button"
            onClick={onClearAll}
            disabled={isUploading}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium transition-all hover:scale-105 disabled:opacity-40"
            style={{
              background: "rgba(244, 63, 94, 0.08)",
              border: "1px solid rgba(244, 63, 94, 0.15)",
              color: "#fb7185",
            }}
          >
            <Trash2 className="w-3.5 h-3.5" />
            Clear All
          </button>

          {hasUnsavedChanges && (
            <button
              type="button"
              onClick={onUpload}
              disabled={isUploading || images.length === 0}
              className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold transition-all hover:scale-105 disabled:opacity-40 disabled:cursor-not-allowed"
              style={{
                background: isUploading
                  ? "rgba(99, 102, 241, 0.2)"
                  : "linear-gradient(135deg, #6366f1, #7c3aed)",
                color: "#fff",
                boxShadow: isUploading ? "none" : "0 4px 15px rgba(99, 102, 241, 0.35)",
              }}
            >
              <Upload className={`w-3.5 h-3.5 ${isUploading ? "animate-bounce" : ""}`} />
              {isUploading ? "Validating..." : "Upload & Validate"}
            </button>
          )}

          {!hasUnsavedChanges && validatedCount > 0 && (
            <button
              type="button"
              onClick={onContinueToPhase2}
              className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold transition-all hover:scale-105"
              style={{
                background: "rgba(16, 185, 129, 0.1)",
                border: "1px solid rgba(16, 185, 129, 0.25)",
                color: "#34d399",
              }}
            >
              <span>Scene Understanding</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Upload progress bar */}
      {isUploading && (
        <div
          className="h-1 rounded-full overflow-hidden"
          style={{ background: "rgba(99, 102, 241, 0.1)" }}
        >
          <div
            className="h-full progress-bar rounded-full"
            style={{ width: `${((uploadingCount > 0 ? 0 : validatedCount) / images.length) * 100}%` }}
          />
        </div>
      )}

      {/* Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {images.map((img) => (
          <ImageCard
            key={img.id}
            image={img}
            onRemove={onRemove}
            onPreview={onPreview}
            disabled={isUploading}
          />
        ))}
      </div>
    </div>
  );
};
