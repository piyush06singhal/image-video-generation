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
  { id: 4, label: "04", title: "Generate", desc: "Image-to-video clips" },
  { id: 5, label: "05", title: "Walkthrough & Review", desc: "Assembly, 360° viewer & audit" },
];

export const StudioPhaseTracker: React.FC<StudioPhaseTrackerProps> = ({
  currentPhase = 1,
  onSelectPhase,
  hasImages = false,
}) => {
  return (
    <div
      className="border-b bg-white/80 backdrop-blur-md shadow-xs"
      style={{
        borderColor: "rgba(30,25,20,0.08)",
      }}
    >
      <div className="max-w-7xl mx-auto px-6 py-4">
        {/* Phase steps */}
        <div className="flex items-center gap-3 overflow-x-auto no-scrollbar">
          {PHASES.map((phase, idx) => {
            const isCurrent = phase.id === currentPhase;
            const isCompleted = phase.id < currentPhase;
            const isLocked = !hasImages && phase.id > 1;
            const isClickable =
              (isCompleted || (phase.id <= 5 && hasImages)) &&
              !isLocked &&
              !!onSelectPhase;

            return (
              <React.Fragment key={phase.id}>
                <button
                  type="button"
                  disabled={!isClickable && !isCurrent}
                  onClick={() => isClickable && onSelectPhase?.(phase.id)}
                  className="flex items-center gap-3 px-4 py-2.5 rounded-xl whitespace-nowrap transition-all shrink-0 group"
                  style={{
                    cursor: isClickable
                      ? "pointer"
                      : isCurrent
                      ? "default"
                      : "not-allowed",
                    background: isCurrent
                      ? "#ffffff"
                      : isCompleted
                      ? "rgba(22,163,74,0.06)"
                      : "transparent",
                    border: isCurrent
                      ? "1.5px solid #c28b2e"
                      : isCompleted
                      ? "1px solid rgba(22,163,74,0.2)"
                      : "1px solid transparent",
                    boxShadow: isCurrent
                      ? "0 4px 14px rgba(194,139,46,0.15)"
                      : "none",
                  }}
                >
                  {/* Circle indicator */}
                  <div
                    className="w-7 h-7 rounded-full flex items-center justify-center shrink-0 text-[11px] font-bold transition-all"
                    style={{
                      background: isCurrent
                        ? "linear-gradient(135deg, #d9a443, #a66e1b)"
                        : isCompleted
                        ? "rgba(22,163,74,0.15)"
                        : "rgba(0,0,0,0.05)",
                      color: isCurrent
                        ? "#ffffff"
                        : isCompleted
                        ? "#15803d"
                        : "#8a8075",
                      boxShadow: isCurrent
                        ? "0 2px 8px rgba(194,139,46,0.4)"
                        : "none",
                    }}
                  >
                    {isCompleted ? (
                      <Check size={13} className="stroke-[2.5]" />
                    ) : isLocked && !isCurrent ? (
                      <Lock size={11} />
                    ) : (
                      phase.label
                    )}
                  </div>

                  {/* Label */}
                  <div className="text-left">
                    <p
                      className="text-xs font-bold leading-none"
                      style={{
                        color: isCurrent
                          ? "#171412"
                          : isCompleted
                          ? "#15803d"
                          : "#8a8075",
                      }}
                    >
                      {phase.title}
                    </p>
                    <p
                      className="text-[10px] leading-none mt-1 hidden sm:block font-medium"
                      style={{ color: isCurrent ? "#c28b2e" : "#8a8075" }}
                    >
                      {phase.desc}
                    </p>
                  </div>

                  {/* Current pulse dot */}
                  {isCurrent && (
                    <span
                      className="w-2 h-2 rounded-full anim-pulse-gold ml-1"
                      style={{ background: "#c28b2e" }}
                    />
                  )}
                </button>

                {/* Connector line */}
                {idx < PHASES.length - 1 && (
                  <div
                    className="flex-1 h-px min-w-[20px] max-w-[50px] shrink-0"
                    style={{
                      background:
                        phase.id < currentPhase
                          ? "linear-gradient(90deg, rgba(22,163,74,0.4), rgba(194,139,46,0.3))"
                          : "rgba(30,25,20,0.1)",
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
