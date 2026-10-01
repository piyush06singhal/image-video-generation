"use client";

import React, { useRef, useState } from "react";
import { UploadCloud, ImagePlus } from "lucide-react";

interface DropzoneProps {
  onFilesSelected: (files: File[]) => void;
  disabled?: boolean;
}

export const Dropzone: React.FC<DropzoneProps> = ({ onFilesSelected, disabled = false }) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    if (!disabled) setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
    if (disabled) return;
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      onFilesSelected(Array.from(e.dataTransfer.files));
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      onFilesSelected(Array.from(e.target.files));
      e.target.value = "";
    }
  };

  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      onClick={() => !disabled && fileInputRef.current?.click()}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if ((e.key === "Enter" || e.key === " ") && !disabled) {
          e.preventDefault();
          fileInputRef.current?.click();
        }
      }}
      className="relative rounded-2xl overflow-hidden transition-all select-none"
      style={{
        cursor: disabled ? "not-allowed" : "pointer",
        border: isDragOver
          ? "2px dashed rgba(99, 102, 241, 0.7)"
          : "2px dashed rgba(148, 163, 184, 0.15)",
        background: isDragOver
          ? "rgba(99, 102, 241, 0.06)"
          : "rgba(15, 23, 42, 0.4)",
        opacity: disabled ? 0.5 : 1,
        transform: isDragOver ? "scale(0.998)" : "scale(1)",
        transition: "all 0.2s ease",
      }}
    >
      {/* Shimmer on drag */}
      {isDragOver && (
        <div
          className="absolute inset-0 pointer-events-none"
          style={{
            background:
              "linear-gradient(135deg, transparent 0%, rgba(99,102,241,0.08) 50%, transparent 100%)",
            animation: "shimmer 1.5s linear infinite",
            backgroundSize: "200% auto",
          }}
        />
      )}

      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept="image/jpeg,image/png,image/webp,image/jpg"
        className="hidden"
        onChange={handleFileInputChange}
        disabled={disabled}
      />

      <div className="py-14 px-8 flex flex-col items-center justify-center max-w-lg mx-auto text-center">
        {/* Icon */}
        <div
          className="w-16 h-16 rounded-2xl flex items-center justify-center mb-5 transition-all"
          style={{
            background: isDragOver
              ? "linear-gradient(135deg, #6366f1, #7c3aed)"
              : "rgba(99, 102, 241, 0.1)",
            border: isDragOver
              ? "1px solid rgba(99,102,241,0.5)"
              : "1px solid rgba(99,102,241,0.15)",
            boxShadow: isDragOver ? "0 0 30px rgba(99,102,241,0.35)" : "none",
            transform: isDragOver ? "scale(1.08)" : "scale(1)",
          }}
        >
          <UploadCloud
            className="w-8 h-8 transition-colors"
            style={{ color: isDragOver ? "#fff" : "#818cf8" }}
          />
        </div>

        <h3 className="text-base font-semibold mb-1.5" style={{ color: "#e2e8f0" }}>
          {isDragOver ? "Release to add photos" : "Drop property photos here"}
        </h3>

        <p className="text-sm mb-5" style={{ color: "#475569" }}>
          or{" "}
          <span
            className="font-semibold underline underline-offset-2"
            style={{ color: "#818cf8" }}
          >
            click to browse files
          </span>
        </p>

        {/* Constraints row */}
        <div
          className="flex items-center gap-4 text-[11px] px-4 py-2 rounded-xl"
          style={{
            background: "rgba(15, 23, 42, 0.6)",
            border: "1px solid rgba(148, 163, 184, 0.1)",
            color: "#64748b",
          }}
        >
          <div className="flex items-center gap-1.5">
            <ImagePlus className="w-3.5 h-3.5" style={{ color: "#6366f1" }} />
            <span>
              <span style={{ color: "#94a3b8", fontWeight: 600 }}>JPG, PNG, WEBP</span>
            </span>
          </div>
          <div
            className="w-px h-3.5"
            style={{ background: "rgba(148, 163, 184, 0.15)" }}
          />
          <span>
            Max{" "}
            <span style={{ color: "#94a3b8", fontWeight: 600 }}>20 MB</span>
          </span>
          <div
            className="w-px h-3.5"
            style={{ background: "rgba(148, 163, 184, 0.15)" }}
          />
          <span>
            Min{" "}
            <span style={{ color: "#94a3b8", fontWeight: 600 }}>512×512</span>
          </span>
        </div>
      </div>
    </div>
  );
};
