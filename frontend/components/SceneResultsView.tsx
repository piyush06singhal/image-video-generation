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
  Loader2,
  ArrowLeft,
} from "lucide-react";

interface SceneResultsViewProps {
  project?: Project;
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
    <div className="space-y-6 anim-fade-up">
      {/* Top Action Bar */}
      <div className="glass-gold rounded-2xl p-6 flex flex-col lg:flex-row lg:items-center justify-between gap-5 border border-[var(--border-2)]">
        <div>
          <div className="flex items-center gap-2.5 mb-1.5 flex-wrap">
            <div className="w-8 h-8 rounded-xl bg-[var(--gold-dim)] border border-[var(--border-2)] text-[var(--gold-2)] flex items-center justify-center">
              <Brain className="w-4 h-4" />
            </div>
            <h3 className="text-lg font-bold font-display text-[var(--text-1)]">
              Visual Scene Understanding
            </h3>
            <span className="badge badge-gold">
              {completedCount} / {images.length} Analyzed
            </span>
          </div>

          <p className="text-xs text-[var(--text-2)] max-w-2xl leading-relaxed">
            Gemini Multimodal AI reads each property photograph to classify room types, architectural
            features, environmental lighting, and camera perspectives. You can adjust labels at any time.
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2.5 flex-wrap">
          <button
            type="button"
            onClick={onBackToUpload}
            disabled={isAnalyzing}
            className="btn-ghost px-3.5 py-2 text-xs font-semibold rounded-xl flex items-center gap-1.5"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Manage Photos</span>
          </button>

          <button
            type="button"
            onClick={() => onAnalyzeAll(false)}
            disabled={isAnalyzing}
            className="btn-gold px-4 py-2 text-xs font-bold rounded-xl flex items-center gap-2 disabled:opacity-50 shadow-md"
          >
            {isAnalyzing ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Analyzing Property…</span>
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
              className="btn-outline-gold px-3.5 py-2 text-xs font-semibold rounded-xl flex items-center gap-1.5 disabled:opacity-50"
              title="Force full re-analysis with vision model"
            >
              <RefreshCw className="w-3.5 h-3.5 text-[var(--gold-2)]" />
              <span>Force Re-analyze All</span>
            </button>
          )}

          {allCompleted && (
            <button
              type="button"
              onClick={onProceedToPhase3}
              className="btn-gold px-4 py-2 text-xs font-bold rounded-xl flex items-center gap-1.5 shadow-lg"
            >
              <span>Continue to Phase 3</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Real-time Analysis Progress Banner */}
      {isAnalyzing && (
        <div className="glass-gold rounded-2xl p-4 flex items-center gap-3 border border-[var(--border-3)] bg-[var(--gold-dim)]">
          <Loader2 className="w-5 h-5 text-[var(--gold-1)] animate-spin shrink-0" />
          <div className="grow space-y-1.5">
            <div className="flex justify-between text-xs font-semibold text-[var(--gold-3)]">
              <span className="flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-[var(--gold-2)]" />
                Multimodal AI model analyzing photographs…
              </span>
              <span className="font-mono">
                {completedCount} of {images.length} images processed
              </span>
            </div>
            <div className="w-full h-2 bg-[var(--bg-0)] rounded-full overflow-hidden border border-[var(--border-1)]">
              <div
                className="h-full bg-gradient-to-r from-[var(--gold-1)] to-[var(--gold-3)] transition-all duration-300 rounded-full"
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
        <div className="glass-gold rounded-2xl p-4 flex items-center gap-2 flex-wrap text-xs">
          <span className="font-semibold text-[var(--text-1)] mr-1 flex items-center gap-1.5">
            <Layers className="w-3.5 h-3.5 text-[var(--gold-2)]" />
            <span>Detected Spaces:</span>
          </span>
          {Object.entries(roomCounts).map(([label, count]) => (
            <span
              key={label}
              className="bg-[var(--bg-0)] border border-[var(--border-1)] text-[var(--text-2)] px-3 py-1 rounded-xl font-medium flex items-center gap-2"
            >
              <span>{label}</span>
              <span className="w-4 h-4 rounded-full bg-[var(--gold-dim)] text-[var(--gold-2)] font-mono text-[10px] flex items-center justify-center font-bold border border-[var(--border-2)]">
                {count}
              </span>
            </span>
          ))}

          {userCorrectedCount > 0 && (
            <span className="ml-auto badge badge-gold">
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
