"use client";

import React from "react";
import { Building, Sparkles, FolderCheck, Hash } from "lucide-react";
import { Project } from "@/types/project";

interface PropertyFormProps {
  propertyName: string;
  onChangeName: (name: string) => void;
  activeProject: Project | null;
  disabled?: boolean;
}

const PROPERTY_SUGGESTIONS = [
  "Modern 3BHK Apartment",
  "Luxury Oceanfront Villa",
  "Downtown Loft Apartment",
  "Contemporary Suburban Home",
  "Penthouse Suite",
];

export const PropertyForm: React.FC<PropertyFormProps> = ({
  propertyName,
  onChangeName,
  activeProject,
  disabled = false,
}) => {
  return (
    <div
      className="rounded-2xl p-5 space-y-4"
      style={{
        background: "rgba(30, 41, 59, 0.5)",
        border: "1px solid rgba(148, 163, 184, 0.1)",
        backdropFilter: "blur(12px)",
      }}
    >
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <label
            htmlFor="property-name"
            className="block text-sm font-semibold"
            style={{ color: "#e2e8f0" }}
          >
            Property Identification
          </label>
          <p className="text-[11px] mt-0.5" style={{ color: "#475569" }}>
            This name will label your project session and appear in exports.
          </p>
        </div>

        {activeProject && (
          <div
            className="flex items-center gap-2 text-xs px-3 py-1.5 rounded-xl shrink-0"
            style={{
              background: "rgba(16, 185, 129, 0.08)",
              border: "1px solid rgba(16, 185, 129, 0.18)",
              color: "#34d399",
            }}
          >
            <FolderCheck className="w-3.5 h-3.5 shrink-0" />
            <span className="font-medium">Project active</span>
            <span
              className="font-mono text-[10px] px-1.5 py-0.5 rounded-md"
              style={{
                background: "rgba(16, 185, 129, 0.1)",
                color: "#6ee7b7",
              }}
            >
              {activeProject.id.slice(-8)}
            </span>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="relative">
        <div
          className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none"
          style={{ color: "#6366f1" }}
        >
          <Building className="w-4 h-4" />
        </div>
        <input
          id="property-name"
          type="text"
          value={propertyName}
          onChange={(e) => onChangeName(e.target.value)}
          placeholder="e.g. Modern 3BHK Apartment, Luxury Penthouse..."
          disabled={disabled}
          maxLength={120}
          className="w-full pl-11 pr-4 py-3 rounded-xl text-sm font-medium transition-all"
          style={{
            background: "rgba(15, 23, 42, 0.7)",
            border: "1px solid rgba(148, 163, 184, 0.15)",
            color: "#f1f5f9",
          }}
        />
        {propertyName && (
          <div
            className="absolute inset-y-0 right-0 pr-3.5 flex items-center"
            style={{ color: "#475569" }}
          >
            <span className="text-[10px] font-mono">{propertyName.length}/120</span>
          </div>
        )}
      </div>

      {/* Suggestions */}
      {!activeProject && (
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-[11px] font-medium" style={{ color: "#475569" }}>
            <Sparkles className="w-3 h-3 inline mr-1" style={{ color: "#6366f1" }} />
            Quick fill:
          </span>
          {PROPERTY_SUGGESTIONS.map((sug) => (
            <button
              key={sug}
              type="button"
              onClick={() => onChangeName(sug)}
              className="text-[11px] px-2.5 py-1 rounded-lg transition-all hover:scale-105"
              style={{
                background: "rgba(99, 102, 241, 0.08)",
                border: "1px solid rgba(99, 102, 241, 0.15)",
                color: "#818cf8",
              }}
            >
              {sug}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};
