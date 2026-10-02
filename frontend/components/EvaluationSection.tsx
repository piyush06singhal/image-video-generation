"use client";

import React, { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { EvaluationCreate, EvaluationSummary } from "@/types/evaluation";
import { TechnicalReportModal } from "@/components/TechnicalReportModal";
import {
  Star,
  Sparkles,
  FileText,
  Trash2,
  CheckCircle2,
  AlertTriangle,
  Loader2,
  User,
  MessageSquare,
  BarChart3,
  HelpCircle,
} from "lucide-react";

interface EvaluationSectionProps {
  projectId: string;
  propertyName?: string;
  onProjectDeleted?: () => void;
}

const EVAL_DIMENSIONS = [
  {
    key: "visual_quality" as const,
    label: "Visual Quality & Realism",
    description: "Photorealistic rendering fidelity, crisp architectural details, lighting naturalness.",
  },
  {
    key: "property_consistency" as const,
    label: "Property Consistency",
    description: "Preservation of layout, furniture, materials, and structures from source photos.",
  },
  {
    key: "scene_ordering" as const,
    label: "Scene Sequence & Flow",
    description: "Logical architectural walkthrough path from exterior/entry to living areas and private rooms.",
  },
  {
    key: "motion_quality" as const,
    label: "Motion Naturalness",
    description: "Smooth, controlled camera trajectories without disorienting sudden turns or artifacts.",
  },
  {
    key: "temporal_stability" as const,
    label: "Temporal Stability",
    description: "Absence of morphing, flickering textures, warping objects, or structural hallucinations.",
  },
  {
    key: "walkthrough_usefulness" as const,
    label: "Walkthrough Practical Usefulness",
    description: "Value as a realistic real estate sales, listing, or buyer inspection tool.",
  },
];

export function EvaluationSection({
  projectId,
  propertyName = "Property",
  onProjectDeleted,
}: EvaluationSectionProps) {
  const [summary, setSummary] = useState<EvaluationSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [submitSuccess, setSubmitSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [ratings, setRatings] = useState<Record<string, number>>({
    visual_quality: 4,
    property_consistency: 4,
    scene_ordering: 5,
    motion_quality: 4,
    temporal_stability: 4,
    walkthrough_usefulness: 5,
  });
  const [reviewerName, setReviewerName] = useState("");
  const [comments, setComments] = useState("");

  // Modals
  const [isReportOpen, setIsReportOpen] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleteConfirmText, setDeleteConfirmText] = useState("");
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const fetchSummary = useCallback(async () => {
    try {
      const data = await api.getEvaluations(projectId);
      setSummary(data);
    } catch (err: unknown) {
      console.error("Failed to load evaluations:", err);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchSummary();
  }, [fetchSummary]);

  const handleRatingChange = (key: string, value: number) => {
    setRatings((prev) => ({ ...prev, [key]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    setSubmitSuccess(false);

    try {
      const payload: EvaluationCreate = {
        visual_quality: ratings.visual_quality,
        property_consistency: ratings.property_consistency,
        scene_ordering: ratings.scene_ordering,
        motion_quality: ratings.motion_quality,
        temporal_stability: ratings.temporal_stability,
        walkthrough_usefulness: ratings.walkthrough_usefulness,
        reviewer_name: reviewerName.trim() || undefined,
        comments: comments.trim() || undefined,
      };

      await api.submitEvaluation(projectId, payload);
      await fetchSummary();
      setSubmitSuccess(true);
      setComments("");
      setTimeout(() => setSubmitSuccess(false), 4000);
    } catch (err: unknown) {
      const e = err as { message?: string };
      setError(e.message || "Failed to submit evaluation");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteProject = async () => {
    if (deleteConfirmText.trim().toLowerCase() !== "delete") {
      setDeleteError("Please type 'DELETE' to confirm.");
      return;
    }

    setIsDeleting(true);
    setDeleteError(null);

    try {
      await api.deleteProject(projectId, true);
      setShowDeleteConfirm(false);
      if (onProjectDeleted) {
        onProjectDeleted();
      } else {
        window.location.href = "/";
      }
    } catch (err: unknown) {
      const e = err as { message?: string };
      setDeleteError(e.message || "Failed to delete project");
      setIsDeleting(false);
    }
  };

  return (
    <div className="space-y-8 pt-6 border-t border-[var(--border-1)]">
      {/* Section Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="badge badge-gold font-mono text-[10px] uppercase">
              Phase 6 Evaluation
            </span>
            <span className="text-xs text-[var(--text-3)] font-mono">
              Prototype Quality Verification
            </span>
          </div>
          <h3 className="text-xl font-bold font-display text-[var(--text-1)] mt-1">
            Walkthrough Evaluation & Quality Audit
          </h3>
          <p className="text-xs text-[var(--text-2)] max-w-xl">
            Assess the generated walkthrough across 6 standardized dimensions or generate a full technical verification report.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setIsReportOpen(true)}
            className="btn-gold px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-2 shadow-sm"
          >
            <FileText className="w-4 h-4" />
            Technical Report
          </button>

          <button
            type="button"
            onClick={() => setShowDeleteConfirm(true)}
            className="p-2 text-[var(--text-3)] hover:text-red-500 hover:bg-red-500/10 rounded-xl transition-colors border border-transparent hover:border-red-500/20"
            title="Clean up project data"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Main Grid: Form + Summary */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Interactive Evaluation Form (7 Cols) */}
        <div className="lg:col-span-7 glass rounded-3xl p-6 border border-[var(--border-1)] space-y-6">
          <div className="flex items-center justify-between border-b border-[var(--border-1)] pb-3">
            <h4 className="text-sm font-bold font-display text-[var(--text-1)] flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-[var(--gold-1)]" />
              Human Quality Assessment
            </h4>
            <span className="text-[11px] text-[var(--text-3)]">
              1 = Poor · 5 = Excellent
            </span>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="space-y-4">
              {EVAL_DIMENSIONS.map((dim) => {
                const currentVal = ratings[dim.key] || 3;
                return (
                  <div
                    key={dim.key}
                    className="p-3 rounded-2xl bg-[var(--bg-1)] border border-[var(--border-1)] hover:border-[var(--border-2)] transition-colors space-y-1.5"
                  >
                    <div className="flex items-center justify-between">
                      <label className="text-xs font-bold text-[var(--text-1)]">
                        {dim.label}
                      </label>
                      <div className="flex items-center gap-1">
                        {[1, 2, 3, 4, 5].map((star) => (
                          <button
                            key={star}
                            type="button"
                            onClick={() => handleRatingChange(dim.key, star)}
                            className={`p-1 transition-transform hover:scale-110 ${
                              star <= currentVal
                                ? "text-[var(--gold-1)] fill-current"
                                : "text-[var(--text-3)] opacity-40 hover:opacity-100"
                            }`}
                          >
                            <Star
                              className={`w-4 h-4 ${
                                star <= currentVal ? "fill-[var(--gold-1)]" : ""
                              }`}
                            />
                          </button>
                        ))}
                        <span className="text-xs font-mono font-bold text-[var(--gold-1)] w-5 text-right ml-1">
                          {currentVal}
                        </span>
                      </div>
                    </div>
                    <p className="text-[11px] text-[var(--text-3)] leading-tight">
                      {dim.description}
                    </p>
                  </div>
                );
              })}
            </div>

            {/* Reviewer Meta */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-[11px] font-bold text-[var(--text-2)] flex items-center gap-1">
                  <User className="w-3 h-3 text-[var(--gold-1)]" />
                  Reviewer Name (Optional)
                </label>
                <input
                  type="text"
                  placeholder="e.g. Lead Evaluator"
                  value={reviewerName}
                  onChange={(e) => setReviewerName(e.target.value)}
                  className="w-full text-xs px-3 py-2 rounded-xl bg-[var(--bg-0)] border border-[var(--border-1)] text-[var(--text-1)] focus:outline-none focus:border-[var(--gold-1)]"
                />
              </div>

              <div className="space-y-1 sm:col-span-2">
                <label className="text-[11px] font-bold text-[var(--text-2)] flex items-center gap-1">
                  <MessageSquare className="w-3 h-3 text-[var(--gold-1)]" />
                  Qualitative Review Notes (Optional)
                </label>
                <textarea
                  rows={2}
                  placeholder="Observations on camera smoothness, texture stability, or lighting..."
                  value={comments}
                  onChange={(e) => setComments(e.target.value)}
                  className="w-full text-xs px-3 py-2 rounded-xl bg-[var(--bg-0)] border border-[var(--border-1)] text-[var(--text-1)] focus:outline-none focus:border-[var(--gold-1)] resize-none"
                />
              </div>
            </div>

            {error && (
              <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-500 text-xs flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {submitSuccess && (
              <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-500 text-xs flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 shrink-0" />
                <span>Evaluation recorded successfully! Summary updated.</span>
              </div>
            )}

            <button
              type="submit"
              disabled={submitting}
              className="btn-gold w-full py-2.5 rounded-xl font-bold text-xs shadow-md glow-gold flex items-center justify-center gap-2"
            >
              {submitting ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  Recording Evaluation...
                </>
              ) : (
                <>
                  <Star className="w-3.5 h-3.5 fill-current" />
                  Submit Evaluation Score
                </>
              )}
            </button>
          </form>
        </div>

        {/* Right: Summary Metrics & Audit Card (5 Cols) */}
        <div className="lg:col-span-5 space-y-6">
          {/* Summary Card */}
          <div className="glass-gold rounded-3xl p-6 border border-[var(--border-2)] space-y-5">
            <div className="flex items-center justify-between border-b border-[var(--border-2)] pb-3">
              <h4 className="text-sm font-bold font-display text-[var(--text-1)] flex items-center gap-2">
                <BarChart3 className="w-4 h-4 text-[var(--gold-1)]" />
                Evaluation Summary
              </h4>
              <span className="badge badge-gold font-mono text-[10px]">
                {summary?.total_evaluations || 0} Review{summary?.total_evaluations === 1 ? "" : "s"}
              </span>
            </div>

            {/* Score Big Display */}
            <div className="flex items-center justify-between">
              <div>
                <p className="text-[11px] text-[var(--text-3)] font-semibold uppercase tracking-wider">
                  Overall Quality Score
                </p>
                <div className="flex items-baseline gap-2 mt-0.5">
                  <span className="text-4xl font-display font-bold text-[var(--text-1)]">
                    {summary?.overall_average !== null && summary?.overall_average !== undefined
                      ? summary.overall_average.toFixed(1)
                      : "—"}
                  </span>
                  <span className="text-xs text-[var(--text-3)] font-medium">/ 5.0</span>
                </div>
              </div>

              <div className="text-right">
                <span className="text-[10px] text-[var(--text-3)] block">
                  {summary && summary.total_evaluations > 0
                    ? "Based on reviewer aggregate"
                    : "Awaiting first submission"}
                </span>
                <button
                  type="button"
                  onClick={() => setIsReportOpen(true)}
                  className="mt-1 text-xs font-bold text-[var(--gold-1)] hover:underline inline-flex items-center gap-1"
                >
                  View full breakdown →
                </button>
              </div>
            </div>

            {/* Dimension Breakdown Bars */}
            <div className="space-y-2.5 pt-2 border-t border-[var(--border-2)]">
              {[
                { label: "Visual Quality", score: summary?.average_visual_quality },
                { label: "Consistency", score: summary?.average_property_consistency },
                { label: "Scene Flow", score: summary?.average_scene_ordering },
                { label: "Motion Quality", score: summary?.average_motion_quality },
                { label: "Stability", score: summary?.average_temporal_stability },
                { label: "Usefulness", score: summary?.average_walkthrough_usefulness },
              ].map((item) => (
                <div key={item.label} className="space-y-1">
                  <div className="flex justify-between text-[11px]">
                    <span className="text-[var(--text-2)] font-medium">{item.label}</span>
                    <span className="font-mono font-bold text-[var(--text-1)]">
                      {item.score !== null && item.score !== undefined ? item.score.toFixed(1) : "—"}
                    </span>
                  </div>
                  <div className="h-1.5 w-full bg-[var(--bg-0)] rounded-full overflow-hidden border border-[var(--border-1)]">
                    <div
                      className="h-full bg-gradient-to-r from-[var(--gold-2)] to-[var(--gold-1)] rounded-full transition-all duration-500"
                      style={{
                        width: `${item.score !== null && item.score !== undefined ? (item.score / 5) * 100 : 0}%`,
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Prototype Verification Guidelines Card */}
          <div className="glass rounded-3xl p-5 border border-[var(--border-1)] space-y-3 bg-[var(--bg-1)]">
            <h5 className="text-xs font-bold text-[var(--text-1)] uppercase tracking-wider font-mono flex items-center gap-2">
              <HelpCircle className="w-3.5 h-3.5 text-[var(--gold-1)]" />
              Evaluation Benchmark Standards
            </h5>
            <ul className="text-[11px] text-[var(--text-2)] space-y-1.5 list-disc list-inside leading-relaxed">
              <li>
                <strong className="text-[var(--text-1)]">4.0+ Visual Quality:</strong> Crisp room geometries without noticeable blur or artifacts.
              </li>
              <li>
                <strong className="text-[var(--text-1)]">4.0+ Consistency:</strong> Features faithfully match uploaded architectural photographs.
              </li>
              <li>
                <strong className="text-[var(--text-1)]">4.5+ Scene Ordering:</strong> Realistic walkthrough trajectory respecting spatial transitions.
              </li>
            </ul>
          </div>
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
          <div className="glass bg-[var(--bg-card)] border border-red-500/30 rounded-3xl p-6 max-w-md w-full shadow-2xl space-y-4">
            <div className="flex items-center gap-3 text-red-500">
              <div className="w-10 h-10 rounded-xl bg-red-500/10 flex items-center justify-center border border-red-500/20">
                <AlertTriangle className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-[var(--text-1)]">
                  Delete Project & Generated Media?
                </h3>
                <p className="text-xs text-[var(--text-3)]">
                  This action is permanent and cannot be undone.
                </p>
              </div>
            </div>

            <p className="text-xs text-[var(--text-2)] leading-relaxed">
              This will permanently delete all uploaded images, scene analyses, generation plans, generated scene clips, assembled walkthrough video, and evaluation logs for <strong className="text-[var(--text-1)]">{propertyName}</strong>.
            </p>

            <div className="space-y-1.5">
              <label className="text-[11px] font-bold text-[var(--text-3)]">
                Type <strong className="text-red-500 font-mono">DELETE</strong> to confirm:
              </label>
              <input
                type="text"
                placeholder="DELETE"
                value={deleteConfirmText}
                onChange={(e) => setDeleteConfirmText(e.target.value)}
                className="w-full text-xs px-3 py-2 rounded-xl bg-[var(--bg-0)] border border-[var(--border-1)] text-[var(--text-1)] focus:outline-none focus:border-red-500 font-mono uppercase"
              />
            </div>

            {deleteError && (
              <p className="text-[11px] text-red-500">{deleteError}</p>
            )}

            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => {
                  setShowDeleteConfirm(false);
                  setDeleteConfirmText("");
                  setDeleteError(null);
                }}
                className="btn-glass px-4 py-2 rounded-xl text-xs font-semibold"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleDeleteProject}
                disabled={isDeleting || deleteConfirmText.trim().toLowerCase() !== "delete"}
                className="px-4 py-2 rounded-xl text-xs font-bold bg-red-500 text-white hover:bg-red-600 transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                {isDeleting ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    Deleting...
                  </>
                ) : (
                  <>
                    <Trash2 className="w-3.5 h-3.5" />
                    Confirm Delete
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Technical Report Modal */}
      <TechnicalReportModal
        projectId={projectId}
        isOpen={isReportOpen}
        onClose={() => setIsReportOpen(false)}
      />
    </div>
  );
}
