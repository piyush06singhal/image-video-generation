"use client";

import React from "react";
import { Check, Lock } from "lucide-react";

interface PhaseTrackerProps {
  currentPhase: number;
  onSelectPhase?: (phaseId: number) => void;
  hasImages?: boolean;
}

const PHASES = [
  { id: 1, label: "01", title: "Upload & Ingestion", shortTitle: "Upload" },
  { id: 2, label: "02", title: "Scene Understanding", shortTitle: "Scene AI" },
  { id: 3, label: "03", title: "Walkthrough Ordering", shortTitle: "Order" },
  { id: 4, label: "04", title: "Image-to-Video", shortTitle: "Video" },
  { id: 5, label: "05", title: "Video Assembly", shortTitle: "Assembly" },
  { id: 6, label: "06", title: "Evaluation", shortTitle: "Eval" },
];

const PHASE_DESCRIPTIONS: Record<number, string> = {
  1: "Images are verified for format, resolution & de-duplicated before storage.",
  2: "Gemini Vision analyzes each photo for room type, features & architectural context.",
  3: "Canonical walkthrough sequence built from scene topology.",
  4: "AI generates interpolated video frames between key scene photographs.",
  5: "Frames stitched into a coherent walkthrough video with transitions.",
  6: "Walkthrough evaluated for coherence, coverage, and visual quality.",
};

export const PhaseTracker: React.FC<PhaseTrackerProps> = ({
  currentPhase = 1,
  onSelectPhase,
  hasImages = false,
}) => {
  return (
    <div
      className="border-b"
      style={{
        background: "rgba(11, 16, 28, 0.8)",
        borderColor: "rgba(148, 163, 184, 0.08)",
      }}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3">
        {/* Phase Steps Row */}
        <div className="flex items-center gap-1 overflow-x-auto no-scrollbar">
          {PHASES.map((phase, idx) => {
            const isCurrent = phase.id === currentPhase;
            const isCompleted = phase.id < currentPhase;
            const isLocked = phase.id > 3 || (!hasImages && phase.id > 1);
            const isClickable = (isCompleted || (phase.id <= 3 && hasImages)) && !isLocked && !!onSelectPhase;


            return (
              <React.Fragment key={phase.id}>
                {/* Step */}
                <button
                  type="button"
                  disabled={!isClickable && !isCurrent}
                  onClick={() => isClickable && onSelectPhase?.(phase.id)}
                  className="flex items-center gap-2 px-3 py-2 rounded-lg whitespace-nowrap transition-all shrink-0"
                  style={{
                    cursor: isClickable ? "pointer" : isCurrent ? "default" : "not-allowed",
                    background: isCurrent
                      ? "rgba(99, 102, 241, 0.15)"
                      : isCompleted
                      ? "rgba(16, 185, 129, 0.06)"
                      : "transparent",
                    border: isCurrent
                      ? "1px solid rgba(99, 102, 241, 0.3)"
                      : isCompleted
                      ? "1px solid rgba(16, 185, 129, 0.15)"
                      : "1px solid transparent",
                  }}
                >
                  {/* Phase Indicator */}
                  <div
                    className="w-6 h-6 rounded-full flex items-center justify-center shrink-0 text-[10px] font-bold"
                    style={{
                      background: isCurrent
                        ? "linear-gradient(135deg, #6366f1, #7c3aed)"
                        : isCompleted
                        ? "rgba(16, 185, 129, 0.2)"
                        : "rgba(148, 163, 184, 0.08)",
                      color: isCurrent ? "#fff" : isCompleted ? "#34d399" : "#475569",
                      boxShadow: isCurrent ? "0 0 10px rgba(99,102,241,0.5)" : "none",
                    }}
                  >
                    {isCompleted ? (
                      <Check className="w-3 h-3" />
                    ) : isLocked && !isCurrent ? (
                      <Lock className="w-2.5 h-2.5" />
                    ) : (
                      phase.label
                    )}
                  </div>

                  {/* Label */}
                  <span
                    className="text-xs font-medium"
                    style={{
                      color: isCurrent ? "#a5b4fc" : isCompleted ? "#34d399" : "#334155",
                    }}
                  >
                    <span className="hidden md:inline">{phase.title}</span>
                    <span className="md:hidden">{phase.shortTitle}</span>
                  </span>

                  {/* Current pulse */}
                  {isCurrent && (
                    <span
                      className="w-1.5 h-1.5 rounded-full animate-pulse"
                      style={{ background: "#818cf8" }}
                    />
                  )}
                </button>

                {/* Connector */}
                {idx < PHASES.length - 1 && (
                  <div
                    className="w-6 h-px shrink-0"
                    style={{
                      background:
                        phase.id < currentPhase
                          ? "linear-gradient(90deg, rgba(16,185,129,0.4), rgba(99,102,241,0.2))"
                          : "rgba(148, 163, 184, 0.08)",
                    }}
                  />
                )}
              </React.Fragment>
            );
          })}
        </div>

        {/* Current phase description */}
        <p className="text-[11px] mt-2" style={{ color: "#475569" }}>
          <span style={{ color: "#6366f1", fontWeight: 600 }}>
            Phase {currentPhase}:
          </span>{" "}
          {PHASE_DESCRIPTIONS[currentPhase]}
        </p>
      </div>
    </div>
  );
};
