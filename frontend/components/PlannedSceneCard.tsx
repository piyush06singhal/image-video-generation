"use client";

import React, { useState } from "react";
import { PlannedScene, CameraMotionType, CAMERA_MOTION_LABELS, TransitionType, TRANSITION_LABELS } from "@/types/plan";
import { SCENE_TYPE_LABELS } from "@/types/scene";
import {
  GripVertical,
  ChevronUp,
  ChevronDown,
  Trash2,
  Maximize2,
  Video,
  Film,
  Sparkles,
  Info,
  CheckCircle2,
  Edit2,
  Check,
  X,
} from "lucide-react";

interface PlannedSceneCardProps {
  scene: PlannedScene;
  index: number;
  totalScenes: number;
  onMoveUp: (index: number) => void;
  onMoveDown: (index: number) => void;
  onRemove: (sceneId: string) => void;
  onInspect: (imageId: string) => void;
  onUpdateLabel: (sceneId: string, newLabel: string) => void;
  onUpdateMotion: (sceneId: string, motion: CameraMotionType) => void;
  onUpdateTransition: (sceneId: string, transition: TransitionType) => void;
  onDragStart?: (index: number) => void;
  onDragOver?: (index: number) => void;
  onDrop?: (index: number) => void;
}

export const PlannedSceneCard: React.FC<PlannedSceneCardProps> = ({
  scene,
  index,
  totalScenes,
  onMoveUp,
  onMoveDown,
  onRemove,
  onInspect,
  onUpdateLabel,
  onUpdateMotion,
  onUpdateTransition,
  onDragStart,
  onDragOver,
  onDrop,
}) => {
  const [isEditingLabel, setIsEditingLabel] = useState(false);
  const [labelDraft, setLabelDraft] = useState(scene.label);
  const [showPromptDetails, setShowPromptDetails] = useState(false);

  const handleSaveLabel = () => {
    if (labelDraft.trim()) {
      onUpdateLabel(scene.scene_id, labelDraft.trim());
    }
    setIsEditingLabel(false);
  };

  const handleCancelLabel = () => {
    setLabelDraft(scene.label);
    setIsEditingLabel(false);
  };

  const previewSrc =
    scene.thumbnail_url || `/api/projects/${scene.image_id}/thumbnail`;

  return (
    <div
      draggable
      onDragStart={() => onDragStart?.(index)}
      onDragOver={(e) => {
        e.preventDefault();
        onDragOver?.(index);
      }}
      onDrop={() => onDrop?.(index)}
      className="glass-gold rounded-2xl p-4 sm:p-5 transition-all duration-200 border border-[var(--border-1)] hover:border-[var(--border-2)] shadow-lg group relative"
    >
      <div className="flex flex-col lg:flex-row lg:items-center gap-4 lg:gap-5 justify-between">
        {/* Left Section: Drag handle + Index + Thumbnail + Labels */}
        <div className="flex items-start sm:items-center gap-3.5 grow">
          {/* Drag Handle & Move Controls */}
          <div className="flex flex-col items-center gap-1 text-[var(--text-3)] pt-1 sm:pt-0">
            <button
              type="button"
              onClick={() => onMoveUp(index)}
              disabled={index === 0}
              className="p-1 hover:text-[var(--gold-2)] disabled:opacity-20 transition-colors"
              title="Move shot earlier in sequence"
            >
              <ChevronUp className="w-4 h-4" />
            </button>
            <div className="cursor-grab active:cursor-grabbing p-0.5 text-[var(--text-3)] hover:text-[var(--gold-2)]">
              <GripVertical className="w-4 h-4" />
            </div>
            <button
              type="button"
              onClick={() => onMoveDown(index)}
              disabled={index === totalScenes - 1}
              className="p-1 hover:text-[var(--gold-2)] disabled:opacity-20 transition-colors"
              title="Move shot later in sequence"
            >
              <ChevronDown className="w-4 h-4" />
            </button>
          </div>

          {/* Sequence Order Badge */}
          <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-[var(--gold-dim)] border border-[var(--border-2)] text-[var(--gold-2)] font-mono font-bold text-sm shadow-md shrink-0">
            {String(scene.order).padStart(2, "0")}
          </div>

          {/* Thumbnail with overlay */}
          <div className="relative w-24 h-18 sm:w-28 sm:h-20 rounded-xl overflow-hidden bg-[var(--bg-0)] shrink-0 border border-[var(--border-1)] group/thumb">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={previewSrc}
              alt={scene.label}
              className="w-full h-full object-cover group-hover/thumb:scale-105 transition-transform duration-300"
            />
            <button
              type="button"
              onClick={() => onInspect(scene.image_id)}
              className="absolute inset-0 bg-[rgba(3,5,7,0.7)] opacity-0 group-hover/thumb:opacity-100 transition-opacity flex items-center justify-center text-white"
              title="Inspect Image"
            >
              <Maximize2 className="w-4 h-4 text-[var(--gold-2)]" />
            </button>
          </div>

          {/* Scene Name, Type & Placement Reason */}
          <div className="space-y-1.5 min-w-0 grow">
            <div className="flex items-center gap-2 flex-wrap">
              {isEditingLabel ? (
                <div className="flex items-center gap-1.5">
                  <input
                    type="text"
                    value={labelDraft}
                    onChange={(e) => setLabelDraft(e.target.value)}
                    className="px-2.5 py-1 text-xs font-semibold rounded-lg bg-[var(--bg-0)] border border-[var(--gold-1)] text-white focus:outline-none"
                    autoFocus
                  />
                  <button
                    type="button"
                    onClick={handleSaveLabel}
                    className="p-1 rounded-md bg-emerald-500/20 text-emerald-300 hover:bg-emerald-500/30"
                  >
                    <Check className="w-3.5 h-3.5" />
                  </button>
                  <button
                    type="button"
                    onClick={handleCancelLabel}
                    className="p-1 rounded-md bg-[var(--bg-0)] text-[var(--text-3)] hover:text-white"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <h4 className="text-sm font-semibold text-[var(--text-1)] truncate">
                    {scene.label}
                  </h4>
                  <button
                    type="button"
                    onClick={() => setIsEditingLabel(true)}
                    className="text-[var(--text-3)] hover:text-[var(--gold-2)] p-0.5"
                    title="Edit custom scene name"
                  >
                    <Edit2 className="w-3 h-3" />
                  </button>
                </div>
              )}

              <span className="badge badge-gold">
                {SCENE_TYPE_LABELS[scene.scene_type] || scene.scene_type}
              </span>

              {scene.user_confirmed && (
                <span className="badge badge-success flex items-center gap-1">
                  <CheckCircle2 className="w-2.5 h-2.5" />
                  Confirmed
                </span>
              )}
            </div>

            <p className="text-xs text-[var(--text-2)] line-clamp-1 leading-relaxed flex items-center gap-1.5" title={scene.reason}>
              <Info className="w-3.5 h-3.5 text-[var(--gold-2)] shrink-0" />
              <span>{scene.reason}</span>
            </p>
          </div>
        </div>

        {/* Right Section: Camera Motion + Transition + Remove Button */}
        <div className="flex items-center gap-3 flex-wrap lg:flex-nowrap justify-between sm:justify-end border-t lg:border-t-0 border-[var(--border-1)] pt-3 lg:pt-0">
          {/* Camera Motion Selector */}
          <div className="space-y-1 min-w-[170px]">
            <label className="text-[10px] font-bold text-[var(--gold-1)] uppercase tracking-wider flex items-center gap-1">
              <Video className="w-3 h-3 text-[var(--gold-2)]" />
              <span>Camera Motion</span>
            </label>
            <select
              value={scene.camera.motion_type}
              onChange={(e) =>
                onUpdateMotion(scene.scene_id, e.target.value as CameraMotionType)
              }
              className="w-full rounded-xl px-2.5 py-1.5 text-xs font-semibold focus:outline-none cursor-pointer"
            >
              {Object.entries(CAMERA_MOTION_LABELS).map(([val, label]) => (
                <option key={val} value={val}>
                  {label}
                </option>
              ))}
            </select>
          </div>

          {/* Inter-scene Transition Selector */}
          {scene.transition_to_next ? (
            <div className="space-y-1 min-w-[150px]">
              <label className="text-[10px] font-bold text-emerald-400 uppercase tracking-wider flex items-center gap-1">
                <Film className="w-3 h-3 text-emerald-400" />
                <span>Transition to Next</span>
              </label>
              <select
                value={scene.transition_to_next.type}
                onChange={(e) =>
                  onUpdateTransition(scene.scene_id, e.target.value as TransitionType)
                }
                className="w-full rounded-xl px-2.5 py-1.5 text-xs font-semibold focus:outline-none cursor-pointer"
              >
                {Object.entries(TRANSITION_LABELS).map(([val, label]) => (
                  <option key={val} value={val}>
                    {label}
                  </option>
                ))}
              </select>
            </div>
          ) : (
            <div className="min-w-[150px] p-2 text-center rounded-xl bg-[var(--bg-0)] border border-[var(--border-1)] text-xs text-[var(--text-3)] font-mono">
              Final Shot (Outro)
            </div>
          )}

          {/* Action Buttons: Prompt Preview Toggle & Remove */}
          <div className="flex items-center gap-1.5 shrink-0 self-end lg:self-center">
            <button
              type="button"
              onClick={() => setShowPromptDetails(!showPromptDetails)}
              className={`px-3 py-1.5 rounded-xl border transition-all text-xs flex items-center gap-1.5 font-semibold ${
                showPromptDetails
                  ? "bg-[var(--gold-dim)] border-[var(--border-3)] text-[var(--gold-2)]"
                  : "btn-ghost"
              }`}
              title="Inspect Video Prompt & Constraints"
            >
              <Sparkles className="w-3.5 h-3.5 text-[var(--gold-2)]" />
              <span className="hidden sm:inline">Prompt</span>
            </button>

            <button
              type="button"
              onClick={() => onRemove(scene.scene_id)}
              className="p-2 rounded-xl bg-red-950/40 text-red-300 border border-red-500/20 hover:bg-red-900/60 transition-all"
              title="Exclude scene from walkthrough video"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Expandable Prompt & Constraints Inspector */}
      {showPromptDetails && (
        <div className="mt-4 pt-3.5 border-t border-[var(--border-1)] text-xs space-y-2.5 anim-fade-up bg-[var(--bg-0)] -mx-4 -mb-4 sm:-mx-5 sm:-mb-5 p-4 sm:p-5 rounded-b-2xl">
          <div className="flex items-center justify-between text-[var(--gold-2)] font-semibold text-xs uppercase tracking-wider">
            <span className="flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-[var(--gold-1)]" />
              Image-to-Video Generation Prompt Specification
            </span>
            <span className="font-mono text-xs">
              Duration: {scene.camera.duration_seconds}s
            </span>
          </div>

          <p className="text-[var(--text-1)] leading-relaxed bg-[var(--bg-card)] p-3 rounded-xl border border-[var(--border-1)] text-xs font-mono">
            {scene.camera.prompt}
          </p>

          <div>
            <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--text-3)] block mb-1">
              Safety &amp; Architectural Preservation Rules:
            </span>
            <div className="flex items-center gap-1.5 flex-wrap">
              {scene.camera.constraints.map((c, i) => (
                <span
                  key={i}
                  className="text-[10px] bg-[var(--bg-card)] border border-[var(--border-1)] text-[var(--text-2)] px-2.5 py-0.5 rounded-md font-mono"
                >
                  ✓ {c}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
