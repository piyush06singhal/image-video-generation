"use client";

import React from "react";
import { Check, Lock } from "lucide-react";

interface StudioPhaseTrackerProps {
  currentPhase: number;
  onSelectPhase?: (phaseId: number) => void;
  hasImages?: boolean;
}

const PHASES = [
  { id: 1, label: "01", title: "Upload", desc: "Ingest & validate images" },
  { id: 2, label: "02", title: "Scene AI", desc: "Gemini scene understanding" },
  { id: 3, label: "03", title: "Plan", desc: "Walkthrough path planning" },
  { id: 4, label: "04", title: "Generate", desc: "Image-to-video generation" },
];

export const StudioPhaseTracker: React.FC<StudioPhaseTrackerProps> = ({
  currentPhase = 1,
  onSelectPhase,
  hasImages = false,
}) => {
  return (
    <div
      className="border-b"
      style={{
        background: "rgba(8,10,13,0.7)",
        borderColor: "rgba(212,168,83,0.07)",
      }}
    >
      <div className="max-w-7xl mx-auto px-6 py-4">
        {/* Phase steps */}
        <div className="flex items-center gap-2 overflow-x-auto no-scrollbar">
          {PHASES.map((phase, idx) => {
            const isCurrent = phase.id === currentPhase;
            const isCompleted = phase.id < currentPhase;
            const isLocked = !hasImages && phase.id > 1;
            const isClickable =
              (isCompleted || (phase.id <= 4 && hasImages)) &&
              !isLocked &&
              !!onSelectPhase;

            return (
              <React.Fragment key={phase.id}>
                <button
                  type="button"
                  disabled={!isClickable && !isCurrent}
                  onClick={() => isClickable && onSelectPhase?.(phase.id)}
                  className="flex items-center gap-2.5 px-4 py-2.5 rounded-xl whitespace-nowrap transition-all shrink-0 group"
                  style={{
                    cursor: isClickable
                      ? "pointer"
                      : isCurrent
                      ? "default"
                      : "not-allowed",
                    background: isCurrent
                      ? "rgba(212,168,83,0.1)"
                      : isCompleted
                      ? "rgba(74,222,128,0.05)"
                      : "transparent",
                    border: isCurrent
                      ? "1px solid rgba(212,168,83,0.3)"
                      : isCompleted
                      ? "1px solid rgba(74,222,128,0.15)"
                      : "1px solid transparent",
                  }}
                >
                  {/* Circle indicator */}
                  <div
                    className="w-6 h-6 rounded-full flex items-center justify-center shrink-0 text-[10px] font-bold transition-all"
                    style={{
                      background: isCurrent
                        ? "linear-gradient(135deg, #d4a853, #8a5e20)"
                        : isCompleted
                        ? "rgba(74,222,128,0.15)"
                        : "rgba(255,255,255,0.04)",
                      color: isCurrent
                        ? "#080a0d"
                        : isCompleted
                        ? "#4ade80"
                        : "#4a3f35",
                      boxShadow: isCurrent
                        ? "0 0 12px rgba(212,168,83,0.5)"
                        : "none",
                    }}
                  >
                    {isCompleted ? (
                      <Check size={11} />
                    ) : isLocked && !isCurrent ? (
                      <Lock size={10} />
                    ) : (
                      phase.label
                    )}
                  </div>

                  {/* Label */}
                  <div className="text-left">
                    <p
                      className="text-xs font-semibold leading-none"
                      style={{
                        color: isCurrent
                          ? "var(--gold-2)"
                          : isCompleted
                          ? "#4ade80"
                          : "#3d3225",
                      }}
                    >
                      {phase.title}
                    </p>
                    <p
                      className="text-[10px] leading-none mt-0.5 hidden sm:block"
                      style={{ color: "var(--text-3)" }}
                    >
                      {phase.desc}
                    </p>
                  </div>

                  {/* Current pulse dot */}
                  {isCurrent && (
                    <span
                      className="w-1.5 h-1.5 rounded-full anim-pulse-gold"
                      style={{ background: "var(--gold-1)" }}
                    />
                  )}
                </button>

                {/* Connector line */}
                {idx < PHASES.length - 1 && (
                  <div
                    className="flex-1 h-px min-w-[20px] max-w-[60px] shrink-0"
                    style={{
                      background:
                        phase.id < currentPhase
                          ? "linear-gradient(90deg, rgba(74,222,128,0.3), rgba(212,168,83,0.2))"
                          : "rgba(212,168,83,0.06)",
                    }}
                  />
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>
    </div>
  );
};
