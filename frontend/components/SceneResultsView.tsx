"use client";

import React from "react";
import { ImageMetadata } from "@/types/image";
import { Project } from "@/types/project";
import { SCENE_TYPE_LABELS, SceneType } from "@/types/scene";
import { SceneCard } from "./SceneCard";
import {
  Brain,
  RefreshCw,
  ArrowRight,
  Sparkles,
  Layers,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  Loader2,
  ArrowLeft,
} from "lucide-react";

interface SceneResultsViewProps {
  project: Project;
  images: ImageMetadata[];
  onAnalyzeAll: (force?: boolean) => Promise<void>;
  onUpdateScene: (imageId: string, newSceneType: SceneType) => Promise<void>;
  onReanalyzeImage: (imageId: string) => Promise<void>;
  onInspectImage: (image: ImageMetadata) => void;
  onBackToUpload: () => void;
  onProceedToPhase3: () => void;
  isAnalyzing: boolean;
}

export const SceneResultsView: React.FC<SceneResultsViewProps> = ({
  project,
  images,
  onAnalyzeAll,
  onUpdateScene,
  onReanalyzeImage,
  onInspectImage,
  onBackToUpload,
  onProceedToPhase3,
  isAnalyzing,
}) => {
  const completedCount = images.filter((img) => img.analysis_status === "completed").length;
  const failedCount = images.filter((img) => img.analysis_status === "failed").length;
  const userCorrectedCount = images.filter(
    (img) => img.scene?.user_corrected === true
  ).length;

  // Calculate room distribution breakdown
  const roomCounts: Record<string, number> = {};
  for (const img of images) {
    if (img.scene?.scene_type) {
      const label = SCENE_TYPE_LABELS[img.scene.scene_type] || img.scene.scene_type;
      roomCounts[label] = (roomCounts[label] || 0) + 1;
    }
  }

  const allCompleted = completedCount > 0 && completedCount === images.length;

  return (
    <div className="space-y-6">
      {/* Top Action Bar */}
      <div className="glass-card-elevated rounded-2xl p-5 sm:p-6 shadow-xl flex flex-col lg:flex-row lg:items-center justify-between gap-5 border border-slate-800">
        <div>
          <div className="flex items-center gap-2.5 mb-1.5 flex-wrap">
            <div className="w-8 h-8 rounded-xl bg-indigo-600/30 border border-indigo-500/40 text-indigo-400 flex items-center justify-center shadow-[0_0_15px_rgba(99,102,241,0.3)]">
              <Brain className="w-4 h-4 text-indigo-300" />
            </div>
            <h3 className="text-base font-semibold text-slate-100">
              Phase 2: Visual Scene Understanding
            </h3>
            <span className="text-[11px] font-mono px-2.5 py-0.5 rounded-full bg-indigo-950/70 text-indigo-300 border border-indigo-500/30 font-semibold">
              {completedCount} / {images.length} Analyzed
            </span>
          </div>

          <p className="text-xs text-slate-400 max-w-2xl leading-relaxed">
            Each photograph undergoes multimodal visual inspection to classify room types, architectural
            features, environmental lighting, and camera perspectives. You can adjust labels at any time.
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2.5 flex-wrap">
          <button
            type="button"
            onClick={onBackToUpload}
            disabled={isAnalyzing}
            className="px-3.5 py-2 text-xs font-medium text-slate-300 hover:text-white bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700/60 rounded-xl transition-all flex items-center gap-1.5"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Manage Photos</span>
          </button>

          <button
            type="button"
            onClick={() => onAnalyzeAll(false)}
            disabled={isAnalyzing}
            className="btn-primary px-4 py-2 text-xs font-semibold rounded-xl flex items-center gap-2 disabled:opacity-50"
          >
            {isAnalyzing ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Analyzing Property...</span>
              </>
            ) : completedCount === 0 ? (
              <>
                <Brain className="w-3.5 h-3.5" />
                <span>Run Scene Understanding</span>
              </>
            ) : (
              <>
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Re-analyze Pending</span>
              </>
            )}
          </button>

          {completedCount > 0 && (
            <button
              type="button"
              onClick={() => onAnalyzeAll(true)}
              disabled={isAnalyzing}
              className="px-3.5 py-2 text-xs font-medium text-slate-300 hover:text-white bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700/60 rounded-xl transition-all flex items-center gap-1.5 disabled:opacity-50"
              title="Force full re-analysis with vision model"
            >
              <RefreshCw className="w-3.5 h-3.5 text-slate-400" />
              <span>Force Re-analyze All</span>
            </button>
          )}

          {allCompleted && (
            <button
              type="button"
              onClick={onProceedToPhase3}
              className="px-4 py-2 text-xs font-semibold text-emerald-950 bg-emerald-400 hover:bg-emerald-300 border border-emerald-300 rounded-xl shadow-[0_0_20px_rgba(16,185,129,0.35)] transition-all flex items-center gap-1.5 font-sans"
            >
              <span>Continue to Phase 3</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Real-time Analysis Progress Banner */}
      {isAnalyzing && (
        <div className="glass-card rounded-2xl p-4 flex items-center gap-3 border border-indigo-500/30 shadow-[0_0_25px_rgba(99,102,241,0.2)] bg-indigo-950/30">
          <Loader2 className="w-5 h-5 text-indigo-400 animate-spin shrink-0" />
          <div className="grow space-y-1.5">
            <div className="flex justify-between text-xs font-semibold text-indigo-200">
              <span className="flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                Multimodal AI model analyzing photographs...
              </span>
              <span className="font-mono text-indigo-300">
                {completedCount} of {images.length} images processed
              </span>
            </div>
            <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
              <div
                className="h-full progress-bar transition-all duration-300"
                style={{
                  width: `${(completedCount / Math.max(1, images.length)) * 100}%`,
                }}
              />
            </div>
          </div>
        </div>
      )}

      {/* Room Distribution Summary Pills */}
      {Object.keys(roomCounts).length > 0 && (
        <div className="glass-card rounded-2xl p-4 flex items-center gap-2 flex-wrap text-xs border border-slate-800">
          <span className="font-semibold text-slate-300 mr-1 flex items-center gap-1.5">
            <Layers className="w-3.5 h-3.5 text-indigo-400" />
            <span>Detected Spaces:</span>
          </span>
          {Object.entries(roomCounts).map(([label, count]) => (
            <span
              key={label}
              className="bg-slate-800/80 border border-slate-700/70 text-slate-200 px-3 py-1 rounded-xl shadow-xs font-medium flex items-center gap-2"
            >
              <span>{label}</span>
              <span className="w-4 h-4 rounded-full bg-indigo-950 text-indigo-300 font-mono text-[10.5px] flex items-center justify-center font-bold border border-indigo-500/30">
                {count}
              </span>
            </span>
          ))}

          {userCorrectedCount > 0 && (
            <span className="ml-auto text-indigo-300 bg-indigo-950/60 border border-indigo-500/30 px-3 py-1 rounded-xl text-[11px] font-medium">
              {userCorrectedCount} manually confirmed
            </span>
          )}
        </div>
      )}

      {/* Grid of Scene Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-5">
        {images.map((img) => (
          <SceneCard
            key={img.id}
            image={img}
            onUpdateScene={onUpdateScene}
            onReanalyzeImage={onReanalyzeImage}
            onInspectImage={onInspectImage}
            isAnalyzing={isAnalyzing}
          />
        ))}
      </div>
    </div>
  );
};
