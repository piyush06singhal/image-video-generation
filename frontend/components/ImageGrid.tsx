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

  return (
    <div className="space-y-5 anim-fade-up">
      {/* Toolbar */}
      <div className="glass-gold rounded-2xl p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        {/* Stats */}
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 rounded-xl bg-[var(--gold-dim)] border border-[var(--border-1)] flex items-center justify-center shrink-0">
            <Layers className="w-5 h-5 text-[var(--gold-2)]" />
          </div>

          <div>
            <p className="text-sm font-semibold text-[var(--text-1)]">
              {images.length} Photograph{images.length !== 1 ? "s" : ""} in Gallery
            </p>
            <div className="flex items-center gap-3 mt-0.5 text-xs">
              {validatedCount > 0 && (
                <span className="flex items-center gap-1 text-emerald-400 font-medium">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  {validatedCount} validated
                </span>
              )}
              {stagedCount > 0 && (
                <span className="flex items-center gap-1 text-[var(--gold-2)] font-medium">
                  <Clock className="w-3.5 h-3.5" />
                  {stagedCount} staged
                </span>
              )}
              {errorCount > 0 && (
                <span className="flex items-center gap-1 text-rose-400 font-medium">
                  <AlertTriangle className="w-3.5 h-3.5" />
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
            className="px-3.5 py-2 rounded-xl text-xs font-semibold bg-red-950/40 border border-red-500/20 text-red-300 hover:bg-red-900/60 transition-all inline-flex items-center gap-1.5 disabled:opacity-40"
          >
            <Trash2 className="w-3.5 h-3.5" />
            Clear Gallery
          </button>

          {hasUnsavedChanges && (
            <button
              type="button"
              onClick={onUpload}
              disabled={isUploading || images.length === 0}
              className="btn-gold px-4 py-2 rounded-xl text-xs font-bold inline-flex items-center gap-2 shadow-lg"
            >
              <Upload className={`w-3.5 h-3.5 ${isUploading ? "animate-spin" : ""}`} />
              {isUploading ? "Uploading & Validating…" : "Upload & Validate"}
            </button>
          )}

          {!hasUnsavedChanges && validatedCount > 0 && (
            <button
              type="button"
              onClick={onContinueToPhase2}
              className="btn-gold px-4 py-2 rounded-xl text-xs font-bold inline-flex items-center gap-2 shadow-lg"
            >
              <span>Proceed to Scene Understanding</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Upload progress indicator */}
      {isUploading && (
        <div className="h-1.5 rounded-full overflow-hidden bg-[var(--bg-card)] border border-[var(--border-1)]">
          <div
            className="h-full bg-gradient-to-r from-[var(--gold-1)] to-[var(--gold-3)] rounded-full transition-all duration-300"
            style={{ width: `${(validatedCount / images.length) * 100}%` }}
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
