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
      className="image-card-hover group relative rounded-2xl overflow-hidden flex flex-col"
      style={{
        background: "rgba(22, 32, 50, 0.8)",
        border: isError
          ? "1px solid rgba(244, 63, 94, 0.3)"
          : isValidated
          ? "1px solid rgba(16, 185, 129, 0.2)"
          : "1px solid rgba(148, 163, 184, 0.1)",
        boxShadow: isValidated
          ? "0 0 0 1px rgba(16, 185, 129, 0.05) inset"
          : "none",
      }}
    >
      {/* Thumbnail */}
      <div className="relative aspect-video bg-slate-900 overflow-hidden">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={image.previewUrl}
          alt={image.name}
          className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
          loading="lazy"
        />

        {/* Dark gradient overlay always present at bottom */}
        <div
          className="absolute inset-x-0 bottom-0 h-1/2 pointer-events-none"
          style={{
            background: "linear-gradient(to top, rgba(8,12,20,0.8), transparent)",
          }}
        />

        {/* Hover action overlay */}
        <div
          className="absolute inset-0 flex items-center justify-center gap-2 p-3 transition-all duration-200"
          style={{
            background: "rgba(8, 12, 20, 0.55)",
            opacity: 0,
          }}
          onMouseEnter={(e) => ((e.currentTarget as HTMLDivElement).style.opacity = "1")}
          onMouseLeave={(e) => ((e.currentTarget as HTMLDivElement).style.opacity = "0")}
        >
          <button
            type="button"
            onClick={() => onPreview(image)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all hover:scale-105"
            style={{
              background: "rgba(255,255,255,0.95)",
              color: "#0f172a",
            }}
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
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all hover:scale-105"
              style={{
                background: "rgba(244, 63, 94, 0.9)",
                color: "#fff",
              }}
            >
              <Trash2 className="w-3.5 h-3.5" />
              Remove
            </button>
          )}
        </div>

        {/* Status badge — top left */}
        <div className="absolute top-2 left-2 z-10">
          {isValidated && (
            <span
              className="flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-md"
              style={{
                background: "rgba(16, 185, 129, 0.15)",
                border: "1px solid rgba(16, 185, 129, 0.25)",
                color: "#34d399",
                backdropFilter: "blur(8px)",
              }}
            >
              <CheckCircle2 className="w-3 h-3" />
              Validated
            </span>
          )}
          {isUploading && (
            <span
              className="flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-md"
              style={{
                background: "rgba(245, 158, 11, 0.15)",
                border: "1px solid rgba(245, 158, 11, 0.2)",
                color: "#fbbf24",
                backdropFilter: "blur(8px)",
              }}
            >
              <Loader2 className="w-3 h-3 animate-spin" />
              Uploading
            </span>
          )}
          {isError && (
            <span
              className="flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-md"
              style={{
                background: "rgba(244, 63, 94, 0.15)",
                border: "1px solid rgba(244, 63, 94, 0.25)",
                color: "#fb7185",
                backdropFilter: "blur(8px)",
              }}
            >
              <AlertTriangle className="w-3 h-3" />
              Rejected
            </span>
          )}
          {isStaged && (
            <span
              className="flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-md"
              style={{
                background: "rgba(99, 102, 241, 0.12)",
                border: "1px solid rgba(99, 102, 241, 0.18)",
                color: "#818cf8",
                backdropFilter: "blur(8px)",
              }}
            >
              <ImageIcon className="w-3 h-3" />
              Staged
            </span>
          )}
        </div>

        {/* Aspect ratio badge — bottom right */}
        {image.aspectRatio && (
          <div
            className="absolute bottom-2 right-2 text-[10px] font-mono px-1.5 py-0.5 rounded-md z-10"
            style={{
              background: "rgba(8, 12, 20, 0.75)",
              color: "#94a3b8",
              backdropFilter: "blur(4px)",
            }}
          >
            {formatAspectRatio(image.aspectRatio)}
          </div>
        )}
      </div>

      {/* Card Info */}
      <div
        className="p-3 flex flex-col gap-1.5 grow"
        style={{ background: "rgba(15, 23, 42, 0.4)" }}
      >
        <h4
          className="text-xs font-medium truncate"
          title={image.name}
          style={{ color: "#cbd5e1" }}
        >
          {image.name}
        </h4>

        <div className="flex items-center justify-between">
          <span className="text-[11px]" style={{ color: "#475569" }}>
            {image.width && image.height
              ? `${image.width} × ${image.height}`
              : "Reading..."}
          </span>
          <span className="text-[11px] font-mono" style={{ color: "#475569" }}>
            {formatFileSize(image.size)}
          </span>
        </div>

        {isError && image.errorMessage && (
          <div
            className="text-[11px] p-2 rounded-lg flex items-start gap-1.5 mt-1"
            style={{
              background: "rgba(244, 63, 94, 0.08)",
              border: "1px solid rgba(244, 63, 94, 0.15)",
              color: "#fb7185",
            }}
          >
            <AlertTriangle className="w-3 h-3 shrink-0 mt-0.5" />
            <span className="line-clamp-2">{image.errorMessage}</span>
          </div>
        )}
      </div>
    </div>
  );
};
