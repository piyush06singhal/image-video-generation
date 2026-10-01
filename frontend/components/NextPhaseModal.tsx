"use client";

import React from "react";
import { X, CheckCircle, Route, Sparkles, ArrowRight, Layers } from "lucide-react";
import { Project } from "@/types/project";

interface NextPhaseModalProps {
  isOpen: boolean;
  onClose: () => void;
  project: Project | null;
}

export const NextPhaseModal: React.FC<NextPhaseModalProps> = ({
  isOpen,
  onClose,
  project,
}) => {
  if (!isOpen || !project) return null;

  const analyzedImages = project.images.filter((img) => img.analysis_status === "completed");
  const userConfirmedCount = project.images.filter((img) => img.scene?.user_corrected).length;

  return (
    <div
      className="fixed inset-0 z-50 modal-backdrop flex items-center justify-center p-4 animate-in fade-in duration-200"
      onClick={onClose}
    >
      <div
        className="glass-card-elevated rounded-3xl max-w-lg w-full p-6 sm:p-7 shadow-2xl space-y-5 border border-slate-700/60"
        style={{ background: "rgba(13, 17, 23, 0.95)" }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-2xl bg-emerald-500/20 border border-emerald-500/30 text-emerald-400 flex items-center justify-center shadow-[0_0_20px_rgba(16,185,129,0.25)]">
              <CheckCircle className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-slate-100">
                Phase 2 Complete: Scene Understanding
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Property: <span className="font-medium text-slate-200">{project.name}</span>
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white rounded-xl hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="bg-slate-900/80 rounded-2xl p-4 border border-slate-800 text-xs space-y-2.5">
          <div className="flex justify-between">
            <span className="text-slate-400">Project Identifier:</span>
            <span className="font-mono font-medium text-indigo-300">{project.id}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Analyzed Photographs:</span>
            <span className="font-semibold text-emerald-400">
              {analyzedImages.length} of {project.image_count} scenes classified
            </span>
          </div>
          {userConfirmedCount > 0 && (
            <div className="flex justify-between">
              <span className="text-slate-400">Manual User Confirmations:</span>
              <span className="font-medium text-indigo-300">{userConfirmedCount} scenes</span>
            </div>
          )}
        </div>

        <div className="glass-card rounded-2xl p-4.5 space-y-2.5 border border-indigo-500/25 bg-indigo-950/20 shadow-[0_0_20px_rgba(99,102,241,0.1)]">
          <div className="flex items-center gap-2 text-indigo-300 font-semibold text-xs uppercase tracking-wider">
            <Route className="w-4 h-4 text-indigo-400" />
            <span>Next Milestone: Phase 3 (Walkthrough Ordering)</span>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed">
            In <strong>Phase 3</strong>, the classified room scenes will be topologically sequenced
            to construct a natural walkthrough route:
          </p>
          <ul className="text-xs text-slate-400 space-y-1.5 list-disc list-inside pl-1">
            <li>Topological route graph planning (Entrance &rarr; Living &rarr; Kitchen &rarr; Bedrooms)</li>
            <li>Camera transition vector estimation between sequential keyframes</li>
            <li>Route timeline and shot duration allocation</li>
          </ul>
        </div>

        <div className="flex justify-end pt-2">
          <button
            type="button"
            onClick={onClose}
            className="btn-primary px-5 py-2.5 text-xs font-semibold rounded-xl shadow-lg hover:scale-102 transition-all flex items-center gap-2"
          >
            <span>Acknowledge &amp; Return</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
};
