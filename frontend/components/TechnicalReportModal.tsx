"use client";

import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { TechnicalReport } from "@/types/evaluation";
import {
  X,
  FileText,
  Download,
  CheckCircle2,
  AlertTriangle,
  Layers,
  Clock,
  Film,
  Camera,
  Compass,
  Star,
  Loader2,
  Copy,
  Check,
} from "lucide-react";

interface TechnicalReportModalProps {
  projectId: string;
  isOpen: boolean;
  onClose: () => void;
}

export function TechnicalReportModal({
  projectId,
  isOpen,
  onClose,
}: TechnicalReportModalProps) {
  const [report, setReport] = useState<TechnicalReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"overview" | "checks" | "ratings" | "raw">("overview");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!isOpen) return;

    let isMounted = true;
    setLoading(true);
    setError(null);

    api
      .getTechnicalReport(projectId)
      .then((data) => {
        if (isMounted) {
          setReport(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err.message || "Failed to load technical report");
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [projectId, isOpen]);

  if (!isOpen) return null;

  const handleDownload = () => {
    if (!report) return;
    const blob = new Blob([report.formatted_text_report], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `property_walkthrough_report_${projectId.slice(0, 8)}.txt`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleCopyRaw = () => {
    if (!report) return;
    navigator.clipboard.writeText(report.formatted_text_report);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const evalSummary = report?.evaluation_summary;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="glass bg-[var(--bg-card)] border border-[var(--border-2)] rounded-3xl w-full max-w-4xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="p-6 border-b border-[var(--border-1)] flex items-center justify-between bg-[var(--bg-1)]">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[var(--gold-dim)] text-[var(--gold-1)] flex items-center justify-center border border-[var(--border-2)]">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-xl font-bold font-display text-[var(--text-1)]">
                Technical Quality & Evaluation Report
              </h2>
              <p className="text-xs text-[var(--text-3)]">
                Complete prototype verification, metrics, automated checks & human evaluation breakdown
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {report && (
              <button
                onClick={handleDownload}
                className="btn-gold px-3.5 py-1.5 rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-sm"
              >
                <Download className="w-3.5 h-3.5" />
                Download .txt
              </button>
            )}
            <button
              onClick={onClose}
              className="p-2 rounded-xl text-[var(--text-3)] hover:text-[var(--text-1)] hover:bg-[var(--bg-2)] transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex items-center gap-2 px-6 pt-3 pb-2 border-b border-[var(--border-1)] bg-[var(--bg-0)]">
          <button
            onClick={() => setActiveTab("overview")}
            className={`px-3.5 py-1.5 text-xs font-semibold rounded-lg transition-all ${
              activeTab === "overview"
                ? "bg-[var(--gold-1)] text-white font-bold"
                : "text-[var(--text-2)] hover:text-[var(--text-1)] hover:bg-[var(--bg-1)]"
            }`}
          >
            System Overview
          </button>
          <button
            onClick={() => setActiveTab("checks")}
            className={`px-3.5 py-1.5 text-xs font-semibold rounded-lg transition-all ${
              activeTab === "checks"
                ? "bg-[var(--gold-1)] text-white font-bold"
                : "text-[var(--text-2)] hover:text-[var(--text-1)] hover:bg-[var(--bg-1)]"
            }`}
          >
            Automated Checks
          </button>
          <button
            onClick={() => setActiveTab("ratings")}
            className={`px-3.5 py-1.5 text-xs font-semibold rounded-lg transition-all ${
              activeTab === "ratings"
                ? "bg-[var(--gold-1)] text-white font-bold"
                : "text-[var(--text-2)] hover:text-[var(--text-1)] hover:bg-[var(--bg-1)]"
            }`}
          >
            Human Evaluation ({evalSummary?.total_evaluations || 0})
          </button>
          <button
            onClick={() => setActiveTab("raw")}
            className={`px-3.5 py-1.5 text-xs font-semibold rounded-lg transition-all ${
              activeTab === "raw"
                ? "bg-[var(--gold-1)] text-white font-bold"
                : "text-[var(--text-2)] hover:text-[var(--text-1)] hover:bg-[var(--bg-1)]"
            }`}
          >
            Raw Formatted Report
          </button>
        </div>

        {/* Body Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {loading && (
            <div className="py-20 flex flex-col items-center justify-center space-y-3">
              <Loader2 className="w-8 h-8 text-[var(--gold-1)] animate-spin" />
              <p className="text-xs text-[var(--text-3)] font-medium">
                Compiling technical audit report...
              </p>
            </div>
          )}

          {error && (
            <div className="p-4 rounded-2xl bg-red-500/10 border border-red-500/20 text-red-500 text-xs flex items-center gap-3">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {report && !loading && (
            <>
              {/* TAB 1: OVERVIEW */}
              {activeTab === "overview" && (
                <div className="space-y-6">
                  {/* Property Card */}
                  <div className="glass rounded-2xl p-5 border border-[var(--border-1)] bg-[var(--bg-1)] grid grid-cols-2 sm:grid-cols-4 gap-4">
                    <div>
                      <p className="text-[10px] uppercase font-bold text-[var(--text-3)]">Property</p>
                      <p className="text-sm font-bold text-[var(--text-1)] truncate mt-0.5">
                        {report.property_name}
                      </p>
                    </div>
                    <div>
                      <p className="text-[10px] uppercase font-bold text-[var(--text-3)]">Project Status</p>
                      <p className="text-xs font-bold text-[var(--gold-1)] capitalize mt-0.5 font-mono">
                        {report.project_status}
                      </p>
                    </div>
                    <div>
                      <p className="text-[10px] uppercase font-bold text-[var(--text-3)]">Created</p>
                      <p className="text-xs text-[var(--text-2)] mt-0.5 font-mono">
                        {new Date(report.created_at).toLocaleDateString()}
                      </p>
                    </div>
                    <div>
                      <p className="text-[10px] uppercase font-bold text-[var(--text-3)]">Report Date</p>
                      <p className="text-xs text-[var(--text-2)] mt-0.5 font-mono">
                        {new Date(report.report_generated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </p>
                    </div>
                  </div>

                  {/* Pipeline Counts */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                    <div className="glass rounded-2xl p-4 border border-[var(--border-1)] space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] text-[var(--text-3)] font-medium">Source Photos</span>
                        <Camera className="w-4 h-4 text-[var(--gold-1)]" />
                      </div>
                      <p className="text-2xl font-bold font-display text-[var(--text-1)]">
                        {report.source_images_count}
                      </p>
                      <p className="text-[10px] text-[var(--text-3)]">
                        {report.analyzed_images_count} analyzed ({report.panoramic_images_count} panoramic)
                      </p>
                    </div>

                    <div className="glass rounded-2xl p-4 border border-[var(--border-1)] space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] text-[var(--text-3)] font-medium">Planned Scenes</span>
                        <Layers className="w-4 h-4 text-[var(--gold-1)]" />
                      </div>
                      <p className="text-2xl font-bold font-display text-[var(--text-1)]">
                        {report.planned_scenes_count}
                      </p>
                      <p className="text-[10px] text-[var(--text-3)]">
                        In ordered graph
                      </p>
                    </div>

                    <div className="glass rounded-2xl p-4 border border-[var(--border-1)] space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] text-[var(--text-3)] font-medium">Generated Clips</span>
                        <Film className="w-4 h-4 text-[var(--gold-1)]" />
                      </div>
                      <p className="text-2xl font-bold font-display text-[var(--text-1)]">
                        {report.generated_clips_count}
                      </p>
                      <p className="text-[10px] text-[var(--text-3)]">
                        Individual scene videos
                      </p>
                    </div>

                    <div className="glass rounded-2xl p-4 border border-[var(--border-1)] space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] text-[var(--text-3)] font-medium">Final Video</span>
                        <Compass className="w-4 h-4 text-[var(--gold-1)]" />
                      </div>
                      <p className="text-2xl font-bold font-display text-[var(--text-1)]">
                        {report.is_video_assembled ? "Ready" : "Pending"}
                      </p>
                      <p className="text-[10px] text-[var(--text-3)]">
                        {report.is_video_assembled ? "Walkthrough compiled" : "Not yet assembled"}
                      </p>
                    </div>
                  </div>

                  {/* Final Video Metadata */}
                  {report.final_video && (
                    <div className="glass rounded-2xl p-5 border border-[var(--border-1)] space-y-3">
                      <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--gold-1)] font-mono">
                        Walkthrough Video Specifications
                      </h3>
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
                        <div>
                          <span className="text-[var(--text-3)]">Duration:</span>{" "}
                          <span className="font-bold text-[var(--text-1)] font-mono">
                            {report.final_video.duration_seconds.toFixed(1)}s
                          </span>
                        </div>
                        <div>
                          <span className="text-[var(--text-3)]">Resolution:</span>{" "}
                          <span className="font-bold text-[var(--text-1)] font-mono">
                            {report.final_video.width} × {report.final_video.height}
                          </span>
                        </div>
                        <div>
                          <span className="text-[var(--text-3)]">Frame Rate:</span>{" "}
                          <span className="font-bold text-[var(--text-1)] font-mono">
                            {report.final_video.fps} FPS
                          </span>
                        </div>
                        <div>
                          <span className="text-[var(--text-3)]">Codec / Format:</span>{" "}
                          <span className="font-bold text-[var(--text-1)] font-mono uppercase">
                            {report.final_video.video_codec} ({report.final_video.format})
                          </span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* TAB 2: AUTOMATED CHECKS */}
              {activeTab === "checks" && (
                <div className="space-y-4">
                  <div className="space-y-3">
                    <div className="glass rounded-2xl p-4 border border-[var(--border-1)] flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        {report.automated_checks.all_scenes_analyzed ? (
                          <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                        ) : (
                          <AlertTriangle className="w-5 h-5 text-amber-500" />
                        )}
                        <div>
                          <p className="text-xs font-bold text-[var(--text-1)]">
                            All Source Images Analyzed
                          </p>
                          <p className="text-[11px] text-[var(--text-3)]">
                            Every uploaded photograph has completed visual understanding and scene classification.
                          </p>
                        </div>
                      </div>
                      <span
                        className={`badge text-[10px] font-mono ${
                          report.automated_checks.all_scenes_analyzed
                            ? "bg-emerald-500/10 text-emerald-500 border border-emerald-500/20"
                            : "bg-amber-500/10 text-amber-500 border border-amber-500/20"
                        }`}
                      >
                        {report.automated_checks.all_scenes_analyzed ? "PASS" : "INCOMPLETE"}
                      </span>
                    </div>

                    <div className="glass rounded-2xl p-4 border border-[var(--border-1)] flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        {report.automated_checks.all_clips_generated ? (
                          <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                        ) : (
                          <AlertTriangle className="w-5 h-5 text-amber-500" />
                        )}
                        <div>
                          <p className="text-xs font-bold text-[var(--text-1)]">
                            All Scene Clips Generated
                          </p>
                          <p className="text-[11px] text-[var(--text-3)]">
                            Individual scene camera animations exist for all planned scenes in the sequence.
                          </p>
                        </div>
                      </div>
                      <span
                        className={`badge text-[10px] font-mono ${
                          report.automated_checks.all_clips_generated
                            ? "bg-emerald-500/10 text-emerald-500 border border-emerald-500/20"
                            : "bg-amber-500/10 text-amber-500 border border-amber-500/20"
                        }`}
                      >
                        {report.automated_checks.all_clips_generated
                          ? "PASS"
                          : `${report.automated_checks.missing_clips_count} MISSING`}
                      </span>
                    </div>

                    <div className="glass rounded-2xl p-4 border border-[var(--border-1)] flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        {report.automated_checks.video_assembled ? (
                          <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                        ) : (
                          <AlertTriangle className="w-5 h-5 text-amber-500" />
                        )}
                        <div>
                          <p className="text-xs font-bold text-[var(--text-1)]">
                            Final Walkthrough Assembled
                          </p>
                          <p className="text-[11px] text-[var(--text-3)]">
                            Walkthrough video file is rendered with smooth transitions and verified integrity.
                          </p>
                        </div>
                      </div>
                      <span
                        className={`badge text-[10px] font-mono ${
                          report.automated_checks.video_assembled
                            ? "bg-emerald-500/10 text-emerald-500 border border-emerald-500/20"
                            : "bg-amber-500/10 text-amber-500 border border-amber-500/20"
                        }`}
                      >
                        {report.automated_checks.video_assembled ? "PASS" : "PENDING"}
                      </span>
                    </div>

                    <div className="glass rounded-2xl p-4 border border-[var(--border-1)] flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        {!report.automated_checks.has_corrupted_output ? (
                          <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                        ) : (
                          <AlertTriangle className="w-5 h-5 text-red-500" />
                        )}
                        <div>
                          <p className="text-xs font-bold text-[var(--text-1)]">
                            Output File Integrity
                          </p>
                          <p className="text-[11px] text-[var(--text-3)]">
                            Rendered video header and video streams are valid and uncorrupted.
                          </p>
                        </div>
                      </div>
                      <span
                        className={`badge text-[10px] font-mono ${
                          !report.automated_checks.has_corrupted_output
                            ? "bg-emerald-500/10 text-emerald-500 border border-emerald-500/20"
                            : "bg-red-500/10 text-red-500 border border-red-500/20"
                        }`}
                      >
                        {!report.automated_checks.has_corrupted_output ? "VERIFIED" : "CORRUPT"}
                      </span>
                    </div>

                    <div className="glass rounded-2xl p-4 border border-[var(--border-1)] flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        {!report.automated_checks.is_outdated_relative_to_plan ? (
                          <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                        ) : (
                          <AlertTriangle className="w-5 h-5 text-amber-500" />
                        )}
                        <div>
                          <p className="text-xs font-bold text-[var(--text-1)]">
                            Plan Synchronization
                          </p>
                          <p className="text-[11px] text-[var(--text-3)]">
                            Walkthrough reflects the most recent generation plan version.
                          </p>
                        </div>
                      </div>
                      <span
                        className={`badge text-[10px] font-mono ${
                          !report.automated_checks.is_outdated_relative_to_plan
                            ? "bg-emerald-500/10 text-emerald-500 border border-emerald-500/20"
                            : "bg-amber-500/10 text-amber-500 border border-amber-500/20"
                        }`}
                      >
                        {!report.automated_checks.is_outdated_relative_to_plan ? "IN SYNC" : "OUTDATED"}
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {/* TAB 3: HUMAN EVALUATION */}
              {activeTab === "ratings" && (
                <div className="space-y-6">
                  {evalSummary && evalSummary.total_evaluations > 0 ? (
                    <div className="space-y-6">
                      {/* Overall Score Banner */}
                      <div className="glass-gold rounded-2xl p-5 border border-[var(--border-2)] flex items-center justify-between">
                        <div>
                          <p className="text-xs text-[var(--text-3)] font-semibold uppercase tracking-wider">
                            Overall Evaluation Score
                          </p>
                          <div className="flex items-baseline gap-2 mt-1">
                            <span className="text-3xl font-display font-bold text-[var(--text-1)]">
                              {evalSummary.overall_average?.toFixed(1) ?? "N/A"}
                            </span>
                            <span className="text-xs text-[var(--text-3)] font-medium">/ 5.0</span>
                          </div>
                        </div>
                        <div className="text-right">
                          <span className="badge badge-gold text-xs font-bold">
                            {evalSummary.total_evaluations} Review{evalSummary.total_evaluations > 1 ? "s" : ""} Recorded
                          </span>
                        </div>
                      </div>

                      {/* 6 Dimension Breakdown */}
                      <div className="space-y-3">
                        <h4 className="text-xs font-bold text-[var(--text-2)] uppercase tracking-wider font-mono">
                          Dimension Averages
                        </h4>

                        {[
                          { label: "Visual Quality", score: evalSummary.average_visual_quality },
                          { label: "Property Consistency", score: evalSummary.average_property_consistency },
                          { label: "Scene Ordering", score: evalSummary.average_scene_ordering },
                          { label: "Motion Quality", score: evalSummary.average_motion_quality },
                          { label: "Temporal Stability", score: evalSummary.average_temporal_stability },
                          { label: "Walkthrough Usefulness", score: evalSummary.average_walkthrough_usefulness },
                        ].map((dim) => (
                          <div key={dim.label} className="glass rounded-xl p-3 border border-[var(--border-1)] flex items-center justify-between gap-4">
                            <span className="text-xs font-semibold text-[var(--text-1)]">
                              {dim.label}
                            </span>
                            <div className="flex items-center gap-3">
                              <div className="w-32 bg-[var(--bg-0)] h-2 rounded-full overflow-hidden border border-[var(--border-1)]">
                                <div
                                  className="h-full bg-gradient-to-r from-[var(--gold-2)] to-[var(--gold-1)] rounded-full"
                                  style={{ width: `${((dim.score || 0) / 5) * 100}%` }}
                                />
                              </div>
                              <span className="text-xs font-bold font-mono text-[var(--gold-1)] w-8 text-right">
                                {dim.score !== null ? dim.score.toFixed(1) : "—"}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>

                      {/* Scene Review Statuses */}
                      {evalSummary.scene_reviews.length > 0 && (
                        <div className="space-y-3">
                          <h4 className="text-xs font-bold text-[var(--text-2)] uppercase tracking-wider font-mono">
                            Per-Scene Review Flags ({evalSummary.scene_reviews.length})
                          </h4>
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                            {evalSummary.scene_reviews.map((rev) => (
                              <div key={rev.review_id} className="glass rounded-xl p-3 border border-[var(--border-1)] text-xs space-y-1">
                                <div className="flex items-center justify-between">
                                  <span className="font-mono font-bold text-[var(--text-1)]">
                                    Scene: {rev.scene_id}
                                  </span>
                                  <span
                                    className={`badge text-[9px] uppercase font-bold ${
                                      rev.status === "acceptable"
                                        ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/20"
                                        : rev.status === "needs_review"
                                        ? "bg-amber-500/10 text-amber-500 border-amber-500/20"
                                        : "bg-red-500/10 text-red-500 border-red-500/20"
                                    }`}
                                  >
                                    {rev.status.replace("_", " ")}
                                  </span>
                                </div>
                                {rev.notes && (
                                  <p className="text-[11px] text-[var(--text-3)] italic">
                                    &ldquo;{rev.notes}&rdquo;
                                  </p>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="text-center py-12 space-y-3 glass rounded-2xl border border-[var(--border-1)]">
                      <Star className="w-10 h-10 text-[var(--text-3)] mx-auto opacity-40" />
                      <p className="text-xs text-[var(--text-2)] font-semibold">
                        No human evaluations recorded yet
                      </p>
                      <p className="text-[11px] text-[var(--text-3)] max-w-sm mx-auto">
                        Submit an evaluation score using the 6-dimension review form below the video player.
                      </p>
                    </div>
                  )}
                </div>
              )}

              {/* TAB 4: RAW FORMATTED REPORT */}
              {activeTab === "raw" && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-[var(--text-3)]">
                      Standardized text format exportable for technical audits
                    </span>
                    <button
                      onClick={handleCopyRaw}
                      className="btn-glass px-3 py-1 text-xs rounded-lg flex items-center gap-1.5"
                    >
                      {copied ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
                      {copied ? "Copied" : "Copy text"}
                    </button>
                  </div>
                  <pre className="p-4 rounded-2xl bg-[var(--bg-0)] border border-[var(--border-1)] text-[11px] font-mono text-[var(--text-2)] overflow-x-auto whitespace-pre-wrap leading-relaxed">
                    {report.formatted_text_report}
                  </pre>
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-[var(--border-1)] bg-[var(--bg-1)] flex items-center justify-between text-xs text-[var(--text-3)]">
          <span>Project ID: <code className="font-mono text-[var(--text-2)]">{projectId.slice(0, 12)}...</code></span>
          <button
            onClick={onClose}
            className="btn-glass px-4 py-2 rounded-xl text-xs font-semibold"
          >
            Close Report
          </button>
        </div>
      </div>
    </div>
  );
}
