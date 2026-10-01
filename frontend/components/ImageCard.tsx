"use client";

import React from "react";
import { Trash2, CheckCircle2, AlertTriangle, Loader2, Maximize2, Image as ImageIcon } from "lucide-react";
import { StagedImage } from "@/types/image";
import { formatAspectRatio, formatFileSize } from "@/lib/utils";

interface ImageCardProps {
  image: StagedImage;
  onRemove: (id: string) => void;
  onPreview: (image: StagedImage) => void;
  disabled?: boolean;
}

export const ImageCard: React.FC<ImageCardProps> = ({
  image,
  onRemove,
  onPreview,
  disabled = false,
}) => {
  const isError = image.status === "error";
  const isValidated = image.status === "validated";
  const isUploading = image.status === "uploading";
  const isStaged = image.status === "staged";

  return (
    <div
      className={`group relative rounded-2xl overflow-hidden flex flex-col glass-gold card-hover ${
        isError ? "border-red-500/30" : isValidated ? "border-emerald-500/30" : "border-[var(--border-1)]"
      }`}
    >
      {/* Thumbnail */}
      <div className="relative aspect-video bg-[var(--bg-1)] overflow-hidden">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={image.previewUrl}
          alt={image.name}
          className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
          loading="lazy"
        />

        {/* Dark gradient overlay */}
        <div className="absolute inset-x-0 bottom-0 h-1/2 bg-gradient-to-t from-[var(--bg-0)] to-transparent pointer-events-none" />

        {/* Hover action overlay */}
        <div className="absolute inset-0 bg-[rgba(3,5,7,0.7)] backdrop-blur-sm opacity-0 group-hover:opacity-100 flex items-center justify-center gap-2 p-3 transition-opacity duration-200">
          <button
            type="button"
            onClick={() => onPreview(image)}
            className="btn-gold px-3 py-1.5 rounded-lg text-xs font-semibold inline-flex items-center gap-1.5 shadow-md"
          >
            <Maximize2 className="w-3.5 h-3.5" />
            Inspect
          </button>

          {!disabled && !isUploading && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onRemove(image.id);
              }}
              className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-red-950/80 text-red-300 border border-red-500/30 hover:bg-red-900/90 transition-all inline-flex items-center gap-1.5"
            >
              <Trash2 className="w-3.5 h-3.5" />
              Remove
            </button>
          )}
        </div>

        {/* Status badge — top left */}
        <div className="absolute top-2 left-2 z-10">
          {isValidated && (
            <span className="badge badge-success">
              <CheckCircle2 className="w-3 h-3" />
              Validated
            </span>
          )}
          {isUploading && (
            <span className="badge badge-warning">
              <Loader2 className="w-3 h-3 animate-spin" />
              Uploading
            </span>
          )}
          {isError && (
            <span className="badge badge-error">
              <AlertTriangle className="w-3 h-3" />
              Rejected
            </span>
          )}
          {isStaged && (
            <span className="badge badge-gold">
              <ImageIcon className="w-3 h-3" />
              Staged
            </span>
          )}
        </div>

        {/* Aspect ratio badge — bottom right */}
        {image.aspectRatio && (
          <div className="absolute bottom-2 right-2 text-[10px] font-mono px-2 py-0.5 rounded-md bg-[rgba(3,5,7,0.85)] border border-[var(--border-1)] text-[var(--text-2)] z-10 backdrop-blur-sm">
            {formatAspectRatio(image.aspectRatio)}
          </div>
        )}
      </div>

      {/* Card Info */}
      <div className="p-3.5 flex flex-col gap-1.5 grow bg-[var(--bg-card)]">
        <h4
          className="text-xs font-semibold text-[var(--text-1)] truncate"
          title={image.name}
        >
          {image.name}
        </h4>

        <div className="flex items-center justify-between text-xs text-[var(--text-3)]">
          <span>
            {image.width && image.height
              ? `${image.width} × ${image.height}`
              : "Reading dimensions…"}
          </span>
          <span className="font-mono text-[var(--text-2)]">
            {formatFileSize(image.size)}
          </span>
        </div>

        {isError && image.errorMessage && (
          <div className="text-xs p-2 rounded-lg bg-red-950/40 border border-red-500/20 text-red-300 flex items-start gap-1.5 mt-1">
            <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5 text-red-400" />
            <span className="line-clamp-2">{image.errorMessage}</span>
          </div>
        )}
      </div>
    </div>
  );
};
