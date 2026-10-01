"use client";

import React, { useState, useEffect } from "react";
import {
  GenerationPlan,
  PlannedScene,
  CameraMotionType,
  TransitionType,
  PlanUpdateRequest,
} from "@/types/plan";
import { Project } from "@/types/project";
import { PlannedSceneCard } from "./PlannedSceneCard";
import {
  Route,
  Sparkles,
  RefreshCw,
  Save,
  Clock,
  Layers,
  ArrowLeft,
  CheckCircle2,
  AlertCircle,
  Eye,
  PlusCircle,
  Loader2,
  Film,
  Compass,
} from "lucide-react";

interface WalkthroughPlanViewProps {
  project: Project;
  plan: GenerationPlan;
  onSavePlan: (updatePayload: PlanUpdateRequest) => Promise<void>;
  onRebuildPlan: () => Promise<void>;
  onInspectImage: (imageId: string) => void;
  onBackToScenes: () => void;
  isSaving: boolean;
  isRebuilding: boolean;
}

export const WalkthroughPlanView: React.FC<WalkthroughPlanViewProps> = ({
  project,
  plan,
  onSavePlan,
  onRebuildPlan,
  onInspectImage,
  onBackToScenes,
  isSaving,
  isRebuilding,
}) => {
  const [scenes, setScenes] = useState<PlannedScene[]>(plan.scenes);
  const [removedSceneIds, setRemovedSceneIds] = useState<string[]>(
    plan.removed_scene_ids || []
  );
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [draggedIdx, setDraggedIdx] = useState<number | null>(null);
  const [showGraphInspector, setShowGraphInspector] = useState(false);

  // Sync state if external plan updates
  useEffect(() => {
    setScenes(plan.scenes);
    setRemovedSceneIds(plan.removed_scene_ids || []);
    setHasUnsavedChanges(false);
  }, [plan]);

  // Move scene up
  const handleMoveUp = (index: number) => {
    if (index === 0) return;
    const updated = [...scenes];
    const temp = updated[index];
    updated[index] = updated[index - 1];
    updated[index - 1] = temp;

    // Recalculate order numbers and transitions
    const reordered = updated.map((s, idx) => ({ ...s, order: idx + 1 }));
    setScenes(reordered);
    setHasUnsavedChanges(true);
  };

  // Move scene down
  const handleMoveDown = (index: number) => {
    if (index === scenes.length - 1) return;
    const updated = [...scenes];
    const temp = updated[index];
    updated[index] = updated[index + 1];
    updated[index + 1] = temp;

    const reordered = updated.map((s, idx) => ({ ...s, order: idx + 1 }));
    setScenes(reordered);
    setHasUnsavedChanges(true);
  };

  // Drag & drop handlers
  const handleDragStart = (index: number) => {
    setDraggedIdx(index);
  };

  const handleDragOver = (index: number) => {
    if (draggedIdx === null || draggedIdx === index) return;
    const updated = [...scenes];
    const draggedItem = updated[draggedIdx];
    updated.splice(draggedIdx, 1);
    updated.splice(index, 0, draggedItem);

    const reordered = updated.map((s, idx) => ({ ...s, order: idx + 1 }));
    setScenes(reordered);
    setDraggedIdx(index);
    setHasUnsavedChanges(true);
  };

  const handleDrop = () => {
    setDraggedIdx(null);
  };

  // Remove scene from active sequence
  const handleRemoveScene = (sceneId: string) => {
    const updatedScenes = scenes
      .filter((s) => s.scene_id !== sceneId)
      .map((s, idx) => ({ ...s, order: idx + 1 }));
    setScenes(updatedScenes);
    setRemovedSceneIds((prev) => Array.from(new Set([...prev, sceneId])));
    setHasUnsavedChanges(true);
  };

  // Restore excluded scene
  const handleRestoreScene = (sceneId: string) => {
    const node = plan.scene_graph?.nodes.find((n) => n.scene_id === sceneId);
    if (!node) return;

    const newOrder = scenes.length + 1;
    const restoredScene: PlannedScene = {
      order: newOrder,
      scene_id: node.scene_id,
      image_id: node.image_id,
      scene_type: node.scene_type,
      label: node.label,
      reason: "Restored into sequence per user plan configuration.",
      camera: {
        motion_type: "slow_forward",
        prompt: `Slow restrained forward camera movement through the ${node.label}. Preserve existing architecture and lighting.`,
        constraints: [
          "do not alter room geometry",
          "do not add furniture",
          "do not remove visible furniture",
          "avoid excessive camera motion",
        ],
        duration_seconds: 4.0,
      },
      thumbnail_url: node.thumbnail_url,
      original_filename: node.original_filename,
      user_confirmed: true,
    };

    setScenes([...scenes, restoredScene]);
    setRemovedSceneIds(removedSceneIds.filter((id) => id !== sceneId));
    setHasUnsavedChanges(true);
  };

  // Edit scene label
  const handleUpdateLabel = (sceneId: string, newLabel: string) => {
    setScenes((prev) =>
      prev.map((s) => (s.scene_id === sceneId ? { ...s, label: newLabel, user_confirmed: true } : s))
    );
    setHasUnsavedChanges(true);
  };

  // Edit camera motion
  const handleUpdateMotion = (sceneId: string, motion: CameraMotionType) => {
    setScenes((prev) =>
      prev.map((s) =>
        s.scene_id === sceneId
          ? {
              ...s,
              camera: {
                ...s.camera,
                motion_type: motion,
              },
            }
          : s
      )
    );
    setHasUnsavedChanges(true);
  };

  // Edit transition
  const handleUpdateTransition = (sceneId: string, transition: TransitionType) => {
    setScenes((prev) =>
      prev.map((s) =>
        s.scene_id === sceneId && s.transition_to_next
          ? {
              ...s,
              transition_to_next: {
                ...s.transition_to_next,
                type: transition,
              },
            }
          : s
      )
    );
    setHasUnsavedChanges(true);
  };

  // Save modified plan
  const handleSave = async () => {
    const payload: PlanUpdateRequest = {
      scenes: scenes.map((s) => ({
        scene_id: s.scene_id,
        order: s.order,
        label: s.label,
        motion_type: s.camera.motion_type,
        camera_prompt: s.camera.prompt,
        transition_type: s.transition_to_next?.type,
        user_confirmed: s.user_confirmed,
      })),
      removed_scene_ids: removedSceneIds,
    };

    await onSavePlan(payload);
    setHasUnsavedChanges(false);
  };

  const totalDuration = scenes.reduce(
    (acc, s) => acc + (s.camera.duration_seconds || 4.0),
    0
  );

  return (
    <div className="space-y-6">
      {/* Top Action Header */}
      <div className="glass-card-elevated rounded-3xl p-5 sm:p-6 shadow-xl flex flex-col lg:flex-row lg:items-center justify-between gap-5 border border-slate-800">
        <div>
          <div className="flex items-center gap-2.5 mb-1.5 flex-wrap">
            <div className="w-8 h-8 rounded-xl bg-indigo-600/30 border border-indigo-500/40 text-indigo-400 flex items-center justify-center shadow-[0_0_15px_rgba(99,102,241,0.3)]">
              <Route className="w-4 h-4 text-indigo-300" />
            </div>
            <h3 className="text-base font-semibold text-slate-100">
              Phase 3: Walkthrough Sequence &amp; Camera Motion Planning
            </h3>
            <span className="text-[11px] font-mono px-2.5 py-0.5 rounded-full bg-indigo-950/70 text-indigo-300 border border-indigo-500/30 font-semibold">
              Plan v{plan.plan_version} &bull; {plan.source === "user" ? "User Customized" : "AI Baseline"}
            </span>
          </div>

          <p className="text-xs text-slate-400 max-w-2xl leading-relaxed">
            Review the sequenced property walkthrough route, camera movements, and transition pacing.
            You can reorder shots via drag &amp; drop, adjust camera strategies, or exclude scenes.
          </p>

          {/* Quick Metrics Bar */}
          <div className="flex items-center gap-3.5 mt-3 text-xs text-slate-300 flex-wrap">
            <div className="flex items-center gap-1.5 bg-slate-900/80 px-2.5 py-1 rounded-xl border border-slate-800">
              <Film className="w-3.5 h-3.5 text-indigo-400" />
              <span>
                <strong>{scenes.length}</strong> Planned Shots
              </span>
            </div>
            <div className="flex items-center gap-1.5 bg-slate-900/80 px-2.5 py-1 rounded-xl border border-slate-800 font-mono">
              <Clock className="w-3.5 h-3.5 text-amber-400" />
              <span>~{totalDuration.toFixed(1)}s Total Runtime</span>
            </div>
            <button
              type="button"
              onClick={() => setShowGraphInspector(!showGraphInspector)}
              className="flex items-center gap-1.5 bg-slate-900/80 hover:bg-slate-800 px-2.5 py-1 rounded-xl border border-slate-800 text-indigo-300 hover:text-white transition-colors"
            >
              <Compass className="w-3.5 h-3.5" />
              <span>{showGraphInspector ? "Hide Scene Graph" : "Inspect Scene Graph"}</span>
            </button>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2.5 flex-wrap">
          <button
            type="button"
            onClick={onBackToScenes}
            disabled={isSaving || isRebuilding}
            className="px-3.5 py-2 text-xs font-medium text-slate-300 hover:text-white bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700/60 rounded-xl transition-all flex items-center gap-1.5"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Manage Scenes</span>
          </button>

          <button
            type="button"
            onClick={onRebuildPlan}
            disabled={isSaving || isRebuilding}
            className="px-3.5 py-2 text-xs font-medium text-slate-300 hover:text-white bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700/60 rounded-xl transition-all flex items-center gap-1.5 disabled:opacity-50"
            title="Re-run AI topological planner from scene analysis"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRebuilding ? "animate-spin text-indigo-400" : ""}`} />
            <span>Regenerate AI Plan</span>
          </button>

          <button
            type="button"
            onClick={handleSave}
            disabled={isSaving || isRebuilding}
            className={`px-4 py-2 text-xs font-semibold rounded-xl shadow-lg transition-all flex items-center gap-2 ${
              hasUnsavedChanges
                ? "bg-emerald-400 hover:bg-emerald-300 text-emerald-950 shadow-[0_0_20px_rgba(16,185,129,0.35)]"
                : "btn-primary"
            } disabled:opacity-50`}
          >
            {isSaving ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Saving Plan...</span>
              </>
            ) : (
              <>
                <Save className="w-3.5 h-3.5" />
                <span>{hasUnsavedChanges ? "Save Changes" : "Save Walkthrough Plan"}</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Unsaved Changes Banner */}
      {hasUnsavedChanges && (
        <div className="glass-card rounded-2xl p-3 px-4 border border-amber-500/30 bg-amber-950/20 text-amber-300 text-xs flex items-center justify-between gap-3 animate-slide-up">
          <div className="flex items-center gap-2 font-medium">
            <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />
            <span>You have modified the walkthrough sequence. Click &quot;Save Changes&quot; to persist your plan.</span>
          </div>
          <button
            type="button"
            onClick={handleSave}
            disabled={isSaving}
            className="px-3 py-1 bg-amber-400 hover:bg-amber-300 text-amber-950 text-xs font-bold rounded-lg shadow-sm shrink-0"
          >
            Save Now
          </button>
        </div>
      )}

      {/* Scene Graph Relationship Inspector (Collapsible) */}
      {showGraphInspector && plan.scene_graph && (
        <div className="glass-card rounded-2xl p-5 border border-indigo-500/30 bg-indigo-950/20 space-y-3 animate-slide-up shadow-xl">
          <div className="flex items-center justify-between font-semibold text-xs text-indigo-300 uppercase tracking-wider">
            <span className="flex items-center gap-2">
              <Compass className="w-4 h-4 text-indigo-400" />
              Candidate Scene Graph Topology ({plan.scene_graph.nodes.length} Nodes &bull; {plan.scene_graph.edges.length} Discovered Edges)
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
            {plan.scene_graph.edges.length > 0 ? (
              plan.scene_graph.edges.map((edge, idx) => {
                const nodeA = plan.scene_graph?.nodes.find((n) => n.scene_id === edge.source_scene_id);
                const nodeB = plan.scene_graph?.nodes.find((n) => n.scene_id === edge.target_scene_id);
                return (
                  <div
                    key={idx}
                    className="bg-slate-900/80 p-3 rounded-xl border border-slate-800 text-xs space-y-1"
                  >
                    <div className="flex items-center justify-between font-medium text-slate-200">
                      <span>{nodeA?.label || edge.source_scene_id} ↔ {nodeB?.label || edge.target_scene_id}</span>
                      <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-500/30">
                        {(edge.confidence * 100).toFixed(0)}%
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400 leading-relaxed">
                      {edge.evidence}
                    </p>
                  </div>
                );
              })
            ) : (
              <p className="text-xs text-slate-500 col-span-2">
                No explicit adjacency edges discovered; sequential ordering relies on standard residential room progression hierarchy.
              </p>
            )}
          </div>
        </div>
      )}

      {/* Ordered Planned Scenes Sequence */}
      <div className="space-y-3.5">
        {scenes.map((scene, idx) => (
          <PlannedSceneCard
            key={scene.scene_id}
            scene={scene}
            index={idx}
            totalScenes={scenes.length}
            onMoveUp={handleMoveUp}
            onMoveDown={handleMoveDown}
            onRemove={handleRemoveScene}
            onInspect={onInspectImage}
            onUpdateLabel={handleUpdateLabel}
            onUpdateMotion={handleUpdateMotion}
            onUpdateTransition={handleUpdateTransition}
            onDragStart={handleDragStart}
            onDragOver={handleDragOver}
            onDrop={handleDrop}
          />
        ))}
      </div>

      {/* Excluded / Removed Scenes Tray */}
      {removedSceneIds.length > 0 && (
        <div className="glass-card-elevated rounded-2xl p-5 border border-slate-800 space-y-3 bg-slate-900/40">
          <div className="flex items-center justify-between font-semibold text-xs text-slate-400 uppercase tracking-wider">
            <span>Excluded from Walkthrough Video ({removedSceneIds.length})</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
            {removedSceneIds.map((sceneId) => {
              const node = plan.scene_graph?.nodes.find((n) => n.scene_id === sceneId);
              if (!node) return null;
              return (
                <div
                  key={sceneId}
                  className="bg-slate-900/80 p-3 rounded-xl border border-slate-800 flex items-center justify-between gap-3"
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <div className="w-12 h-10 rounded-lg overflow-hidden bg-slate-950 shrink-0 border border-slate-800">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={node.thumbnail_url || `/api/projects/${node.image_id}/thumbnail`}
                        alt={node.label}
                        className="w-full h-full object-cover"
                      />
                    </div>
                    <div className="truncate">
                      <h5 className="text-xs font-semibold text-slate-300 truncate">
                        {node.label}
                      </h5>
                      <span className="text-[10px] text-slate-500 font-mono">
                        {node.scene_type}
                      </span>
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={() => handleRestoreScene(sceneId)}
                    className="p-1.5 text-xs font-medium text-indigo-300 hover:text-white bg-indigo-950/60 hover:bg-indigo-900/80 rounded-lg border border-indigo-500/30 transition-colors flex items-center gap-1 shrink-0"
                    title="Restore into active walkthrough order"
                  >
                    <PlusCircle className="w-3.5 h-3.5" />
                    <span>Restore</span>
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
