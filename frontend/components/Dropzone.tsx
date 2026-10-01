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
      className={`relative rounded-2xl overflow-hidden transition-all duration-300 select-none cursor-pointer border-2 border-dashed ${
        isDragOver
          ? "border-[var(--gold-2)] bg-[var(--gold-dim)] scale-[0.995] shadow-[0_0_30px_var(--gold-glow)]"
          : "border-[var(--border-2)] bg-[var(--bg-card)] hover:border-[var(--border-3)] hover:bg-[var(--gold-subtle)]"
      } ${disabled ? "opacity-40 cursor-not-allowed" : ""}`}
    >
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
        {/* Upload Icon */}
        <div
          className={`w-16 h-16 rounded-2xl flex items-center justify-center mb-5 transition-transform duration-300 ${
            isDragOver
              ? "bg-gradient-to-br from-[var(--gold-1)] to-[#8a5e20] text-[#080a0d] scale-110 shadow-lg shadow-[var(--gold-glow)]"
              : "bg-[var(--gold-dim)] border border-[var(--border-1)] text-[var(--gold-2)]"
          }`}
        >
          <UploadCloud className="w-8 h-8" />
        </div>

        <h3 className="text-lg font-semibold text-[var(--text-1)] mb-1.5 font-display">
          {isDragOver ? "Drop photographs right here" : "Upload Property Photographs"}
        </h3>

        <p className="text-sm text-[var(--text-2)] mb-6">
          Drag & drop your property photos here, or{" "}
          <span className="font-semibold text-[var(--gold-2)] underline underline-offset-4 hover:text-[var(--gold-3)]">
            browse from device
          </span>
        </p>

        {/* Requirements pills */}
        <div className="flex flex-wrap items-center justify-center gap-3 text-xs text-[var(--text-3)]">
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-full border border-[var(--border-1)] bg-[var(--bg-0)]">
            <ImagePlus className="w-3.5 h-3.5 text-[var(--gold-2)]" />
            <span className="text-[var(--text-2)] font-medium">JPG, PNG, WEBP</span>
          </div>
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-full border border-[var(--border-1)] bg-[var(--bg-0)]">
            <span className="text-[var(--text-2)] font-medium">Max 20MB per photo</span>
          </div>
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-full border border-[var(--border-1)] bg-[var(--bg-0)]">
            <span className="text-[var(--text-2)] font-medium">Min 512×512 resolution</span>
          </div>
        </div>
      </div>
    </div>
  );
};
