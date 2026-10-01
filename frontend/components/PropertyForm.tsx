"use client";

import React from "react";
import { Building, Sparkles, FolderCheck } from "lucide-react";
import { Project } from "@/types/project";

interface PropertyFormProps {
  propertyName: string;
  onChangeName?: (name: string) => void;
  onPropertyNameChange?: (name: string) => void;
  activeProject?: Project | null;
  project?: Project | null;
  disabled?: boolean;
}

const PROPERTY_SUGGESTIONS = [
  "Modern 3BHK Luxury Apartment",
  "Oceanfront Villa Estate",
  "Downtown Sky Penthouse",
  "Contemporary Suburban Retreat",
  "Minimalist Architectural Home",
];

export const PropertyForm: React.FC<PropertyFormProps> = ({
  propertyName,
  onChangeName,
  onPropertyNameChange,
  activeProject,
  project,
  disabled = false,
}) => {
  const currentProject = activeProject || project;
  const handleChange = (val: string) => {
    if (onChangeName) onChangeName(val);
    if (onPropertyNameChange) onPropertyNameChange(val);
  };

  return (
    <div className="glass-gold rounded-2xl p-6 space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <label
            htmlFor="property-name"
            className="block text-sm font-semibold text-[var(--text-1)]"
          >
            Property Name &amp; Identification
          </label>
          <p className="text-xs text-[var(--text-3)] mt-0.5">
            Labels your property walkthrough project and generated video metadata.
          </p>
        </div>

        {currentProject && (
          <div className="badge badge-success flex items-center gap-1.5 px-3 py-1 text-xs shrink-0">
            <FolderCheck className="w-3.5 h-3.5 shrink-0" />
            <span>Active Session</span>
            <span className="font-mono text-[10px] text-emerald-300 font-bold ml-1">
              #{currentProject.id.slice(-6)}
            </span>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="relative flex items-center">
        <div className="absolute left-4 top-1/2 -translate-y-1/2 text-[var(--gold-1)] pointer-events-none z-10 flex items-center justify-center w-5 h-5">
          <Building className="w-4 h-4" />
        </div>
        <input
          id="property-name"
          type="text"
          value={propertyName}
          onChange={(e) => handleChange(e.target.value)}
          placeholder="e.g. Luxury Architectural Villa, Oceanfront Penthouse..."
          disabled={disabled}
          maxLength={120}
          className="w-full pl-12 pr-20 py-3.5 rounded-xl text-sm font-medium focus:ring-2 focus:ring-[var(--gold-1)] transition-all bg-[var(--bg-card)] border border-[var(--border-2)] text-[var(--text-1)] placeholder:text-[var(--text-3)]"
        />
        {propertyName && (
          <div className="absolute right-4 top-1/2 -translate-y-1/2 flex items-center text-[var(--text-3)] pointer-events-none">
            <span className="text-[11px] font-mono">{propertyName.length}/120</span>
          </div>
        )}
      </div>

      {/* Quick Suggestions */}
      {!currentProject && (
        <div className="flex items-center gap-2 flex-wrap pt-1">
          <span className="text-xs text-[var(--text-3)] flex items-center gap-1.5 font-medium">
            <Sparkles className="w-3.5 h-3.5 text-[var(--gold-2)]" />
            Presets:
          </span>
          {PROPERTY_SUGGESTIONS.map((sug) => (
            <button
              key={sug}
              type="button"
              onClick={() => handleChange(sug)}
              className="text-xs px-3 py-1 rounded-lg border border-[var(--border-1)] bg-[var(--gold-dim)] text-[var(--gold-2)] hover:border-[var(--border-2)] hover:bg-[var(--gold-glow)] transition-all font-medium"
            >
              {sug}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};
