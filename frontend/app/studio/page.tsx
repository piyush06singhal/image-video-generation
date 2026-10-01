"use client";

import React, { useState, useEffect, useCallback } from "react";
import { StudioHeader } from "@/components/StudioHeader";
import { StudioPhaseTracker } from "@/components/StudioPhaseTracker";
import { PropertyForm } from "@/components/PropertyForm";
import { Dropzone } from "@/components/Dropzone";
import { ImageCard } from "@/components/ImageCard";
import { SceneResultsView } from "@/components/SceneResultsView";
import { WalkthroughPlanView } from "@/components/WalkthroughPlanView";
import { GenerationView } from "@/components/GenerationView";
import { ImagePreviewModal } from "@/components/ImagePreviewModal";
import { NextPhaseModal } from "@/components/NextPhaseModal";
import { ImageMetadata, StagedImage } from "@/types/image";
import { GenerationPlan, PlanUpdateRequest } from "@/types/plan";
import { Project } from "@/types/project";
import { SceneType } from "@/types/scene";
import { api, ApiError } from "@/lib/api";
import { extractLocalImageDimensions, generateClientId } from "@/lib/utils";
import {
  Upload,
  ArrowRight,
  CheckCircle2,
  AlertCircle,
  Loader2,
  X,
  Sparkles,
  Trash2,
  Film,
} from "lucide-react";

/* ── Inline alert ── */
function StudioAlert({
  type,
  title,
  message,
  onClose,
}: {
  type: "error" | "success" | "warning" | "info";
  title?: string;
  message: string;
  onClose: () => void;
}) {
  const colors = {
    error:   { bg: "rgba(248,113,113,0.08)", border: "rgba(248,113,113,0.25)", text: "#f87171", icon: AlertCircle },
    success: { bg: "rgba(74,222,128,0.08)",  border: "rgba(74,222,128,0.25)",  text: "#4ade80", icon: CheckCircle2 },
    warning: { bg: "rgba(251,191,36,0.08)",  border: "rgba(251,191,36,0.25)",  text: "#fbbf24", icon: AlertCircle },
    info:    { bg: "rgba(212,168,83,0.08)",  border: "rgba(212,168,83,0.25)",  text: "var(--gold-2)", icon: Sparkles },
  }[type];
  const Icon = colors.icon;
  return (
    <div
      className="flex items-start gap-3 px-4 py-3 rounded-xl mb-6 anim-fade-up backdrop-blur-md"
      style={{ background: colors.bg, border: `1px solid ${colors.border}` }}
    >
      <Icon size={16} style={{ color: colors.text, flexShrink: 0, marginTop: 2 }} />
      <div className="flex-1 min-w-0">
        {title && <p className="text-sm font-semibold" style={{ color: colors.text }}>{title}</p>}
        <p className="text-xs text-[var(--text-2)] mt-0.5">{message}</p>
      </div>
      <button onClick={onClose} className="text-[var(--text-3)] hover:text-white transition-colors">
        <X size={14} />
      </button>
    </div>
  );
}

/* ══════════════════════════════
   MAIN STUDIO PAGE
══════════════════════════════ */
export default function StudioPage() {
  const [currentPhase, setCurrentPhase] = useState(1);
  const [propertyName, setPropertyName] = useState("Luxury Architectural Villa");
  const [stagedImages, setStagedImages] = useState<StagedImage[]>([]);
  const [activeProject, setActiveProject] = useState<Project | null>(null);
  const [currentPlan, setCurrentPlan] = useState<GenerationPlan | null>(null);

  const [isUploading, setIsUploading] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isLoadingPlan, setIsLoadingPlan] = useState(false);
  const [isSavingPlan, setIsSavingPlan] = useState(false);
  const [isRebuildingPlan, setIsRebuildingPlan] = useState(false);

  const [isBackendHealthy, setIsBackendHealthy] = useState<boolean | null>(null);
  const [isCheckingHealth, setIsCheckingHealth] = useState(false);
  const [alert, setAlert] = useState<{
    type: "error" | "success" | "warning" | "info";
    title?: string;
    message: string;
  } | null>(null);
  const [selectedPreviewImage, setSelectedPreviewImage] = useState<ImageMetadata | StagedImage | null>(null);
  const [isNextPhaseModalOpen, setIsNextPhaseModalOpen] = useState(false);

  /* ── Health check ── */
  const checkHealth = useCallback(async () => {
    setIsCheckingHealth(true);
    try {
      const res = await api.checkHealth();
      setIsBackendHealthy(res?.status === "healthy");
    } catch {
      setIsBackendHealthy(false);
    } finally {
      setIsCheckingHealth(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    const run = async () => {
      setIsCheckingHealth(true);
      try {
        const res = await api.checkHealth();
        if (active) setIsBackendHealthy(res?.status === "healthy");
      } catch {
        if (active) setIsBackendHealthy(false);
      } finally {
        if (active) setIsCheckingHealth(false);
      }
    };
    run();
    return () => {
      active = false;
    };
  }, []);

  /* ── Load plan when entering phase 3 ── */
  useEffect(() => {
    let active = true;
    if (currentPhase === 3 && activeProject && !currentPlan) {
      const fetchPlan = async () => {
        setIsLoadingPlan(true);
        try {
          const plan = await api.getPlan(activeProject.id);
          if (active) setCurrentPlan(plan);
        } catch (err) {
          if (active) {
            setAlert({
              type: "error",
              title: "Plan Load Failed",
              message: err instanceof ApiError ? err.message : "Failed to load walkthrough plan.",
            });
          }
        } finally {
          if (active) setIsLoadingPlan(false);
        }
      };
      fetchPlan();
    }
    return () => {
      active = false;
    };
  }, [currentPhase, activeProject, currentPlan]);

  /* ── File staging ── */
  const handleFilesSelected = async (newFiles: File[]) => {
    if (!newFiles.length) return;
    const allowed = ["image/jpeg", "image/png", "image/webp", "image/jpg"];
    const maxSize = 20 * 1024 * 1024;
    const valid: StagedImage[] = [];
    const rejected: string[] = [];

    for (const file of newFiles) {
      if (!allowed.includes(file.type)) {
        rejected.push(`${file.name} (unsupported format)`);
        continue;
      }
      if (file.size > maxSize) {
        rejected.push(`${file.name} (exceeds 20 MB)`);
        continue;
      }

      const alreadyStaged = stagedImages.some((s) => s.file && s.file.name === file.name && s.file.size === file.size);
      if (alreadyStaged) continue;

      const objectUrl = URL.createObjectURL(file);
      let w = 0, h = 0;
      try {
        const dims = await extractLocalImageDimensions(file);
        w = dims.width;
        h = dims.height;
      } catch {}
      valid.push({
        id: generateClientId(),
        name: file.name,
        size: file.size,
        file,
        previewUrl: objectUrl,
        width: w,
        height: h,
        aspectRatio: w > 0 && h > 0 ? w / h : undefined,
        status: "staged",
      });
    }

    if (rejected.length) {
      setAlert({ type: "warning", title: "Some files skipped", message: rejected.join(" · ") });
    }
    if (valid.length) setStagedImages((prev) => [...prev, ...valid]);
  };

  const handleRemoveStaged = (id: string) => {
    setStagedImages((prev) => {
      const img = prev.find((s) => s.id === id);
      if (img) URL.revokeObjectURL(img.previewUrl);
      return prev.filter((s) => s.id !== id);
    });
  };

  const handleClearStaged = () => {
    stagedImages.forEach((s) => URL.revokeObjectURL(s.previewUrl));
    setStagedImages([]);
  };

  /* ── Upload ── */
  const handleUpload = async () => {
    if (!stagedImages.length) return;
    setIsUploading(true);
    setAlert(null);
    try {
      const project = activeProject || (await api.createProject(propertyName.trim() || "Property"));
      const files = stagedImages
        .map((s) => s.file)
        .filter((f): f is File => Boolean(f));

      const result = await api.uploadImages(project.id, files);
      stagedImages.forEach((s) => URL.revokeObjectURL(s.previewUrl));
      setStagedImages([]);
      const updated = await api.getProject(project.id);
      setActiveProject(updated);
      setAlert({
        type: "success",
        message: `${result.total_accepted} photograph${result.total_accepted > 1 ? "s" : ""} uploaded and verified.`,
      });
    } catch (err) {
      setAlert({
        type: "error",
        title: "Upload Failed",
        message: err instanceof ApiError ? err.message : "Upload failed.",
      });
    } finally {
      setIsUploading(false);
    }
  };

  /* ── Analyse ── */
  const handleAnalyzeAll = async (force: boolean = false) => {
    if (!activeProject) return;
    setIsAnalyzing(true);
    setAlert(null);
    try {
      const project = await api.analyzeProject(activeProject.id, force);
      setActiveProject(project);
      setAlert({ type: "success", message: "Visual scene intelligence analysis complete." });
    } catch (err) {
      setAlert({
        type: "error",
        title: "Analysis Failed",
        message: err instanceof ApiError ? err.message : "Analysis failed.",
      });
    } finally {
      setIsAnalyzing(false);
    }
  };

  /* ── Single Image Reanalyze ── */
  const handleReanalyzeImage = async (imageId: string) => {
    if (!activeProject) return;
    setIsAnalyzing(true);
    try {
      const project = await api.analyzeProject(activeProject.id, true, [imageId]);
      setActiveProject(project);
    } catch (err) {
      setAlert({
        type: "error",
        title: "Re-analysis Failed",
        message: err instanceof ApiError ? err.message : "Failed to re-analyze image.",
      });
    } finally {
      setIsAnalyzing(false);
    }
  };

  /* ── Scene correction ── */
  const handleUpdateScene = async (imageId: string, newSceneType: SceneType) => {
    if (!activeProject) return;
    try {
      const updatedImage = await api.updateImageScene(activeProject.id, imageId, {
        scene_type: newSceneType,
      });
      setActiveProject((prev) =>
        prev
          ? {
              ...prev,
              images: prev.images.map((img) =>
                img.id === imageId ? updatedImage : img
              ),
            }
          : prev
      );
    } catch (err) {
      setAlert({
        type: "error",
        title: "Correction Failed",
        message: err instanceof ApiError ? err.message : "Failed to save correction.",
      });
    }
  };

  /* ── Plan save ── */
  const handleSavePlan = async (updates: PlanUpdateRequest) => {
    if (!activeProject) return;
    setIsSavingPlan(true);
    try {
      const plan = await api.updatePlan(activeProject.id, updates);
      setCurrentPlan(plan);
      setAlert({ type: "success", message: "Walkthrough route plan saved successfully." });
    } catch (err) {
      setAlert({
        type: "error",
        title: "Save Failed",
        message: err instanceof ApiError ? err.message : "Failed to save plan.",
      });
    } finally {
      setIsSavingPlan(false);
    }
  };

  const handleRebuildPlan = async () => {
    if (!activeProject) return;
    setIsRebuildingPlan(true);
    try {
      const plan = await api.rebuildPlan(activeProject.id);
      setCurrentPlan(plan);
      setAlert({ type: "info", message: "Walkthrough plan regenerated with AI model." });
    } catch (err) {
      setAlert({
        type: "error",
        title: "Rebuild Failed",
        message: err instanceof ApiError ? err.message : "Failed to rebuild plan.",
      });
    } finally {
      setIsRebuildingPlan(false);
    }
  };

  const handleInspectByImageId = (imageId: string) => {
    const found = activeProject?.images.find((img) => img.id === imageId);
    if (found) setSelectedPreviewImage(found);
  };

  /* ── Phase gate flags ── */
  const uploadedImages = activeProject?.images ?? [];
  const hasImages = uploadedImages.length > 0;

  return (
    <div className="min-h-screen bg-[var(--bg-0)] text-[var(--text-1)]">
      {/* Sticky Studio Header */}
      <StudioHeader
        isBackendHealthy={isBackendHealthy}
        onRetryHealth={checkHealth}
        isCheckingHealth={isCheckingHealth}
      />

      {/* Phase Steps Tracker */}
      <StudioPhaseTracker
        currentPhase={currentPhase}
        onSelectPhase={setCurrentPhase}
        hasImages={hasImages}
      />

      {/* Main Studio Container */}
      <main className="max-w-7xl mx-auto px-6 py-10">
        {/* Alerts */}
        {alert && (
          <StudioAlert
            type={alert.type}
            title={alert.title}
            message={alert.message}
            onClose={() => setAlert(null)}
          />
        )}

        {/* ── PHASE 1: UPLOAD & INGESTION ── */}
        {currentPhase === 1 && (
          <div className="space-y-8 anim-fade-up">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <Upload size={16} className="text-[var(--gold-1)]" />
                <p className="text-xs font-semibold tracking-[0.15em] uppercase text-[var(--gold-1)]">
                  Phase 01
                </p>
              </div>
              <h2 className="font-display text-3xl font-bold text-[var(--text-1)]">
                Property Ingestion &amp; Image Validation
              </h2>
              <p className="text-sm text-[var(--text-2)] mt-1">
                Drop your high-resolution property photographs. Each image is verified, quality-scored, and securely cataloged.
              </p>
            </div>

            <div className="grid lg:grid-cols-3 gap-6 items-start">
              {/* Left 2 Cols: Form + Dropzone */}
              <div className="lg:col-span-2 space-y-6">
                <PropertyForm
                  propertyName={propertyName}
                  onPropertyNameChange={setPropertyName}
                  activeProject={activeProject}
                  disabled={isUploading}
                />

                <Dropzone
                  onFilesSelected={handleFilesSelected}
                  disabled={isUploading}
                />

                {/* Staged files action bar */}
                {stagedImages.length > 0 && (
                  <div className="glass-gold rounded-2xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4 border border-[var(--border-2)]">
                    <div className="flex items-center gap-2">
                      <span className="w-2.5 h-2.5 rounded-full bg-[var(--gold-1)] animate-pulse" />
                      <span className="text-sm font-semibold text-[var(--text-1)]">
                        {stagedImages.length} image{stagedImages.length !== 1 ? "s" : ""} ready to upload
                      </span>
                    </div>

                    <div className="flex items-center gap-2 w-full sm:w-auto">
                      <button
                        type="button"
                        onClick={handleClearStaged}
                        disabled={isUploading}
                        className="px-3.5 py-2 text-xs font-semibold bg-red-950/40 text-red-300 border border-red-500/20 rounded-xl hover:bg-red-900/60 transition-all flex items-center gap-1.5"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                        Clear
                      </button>

                      <button
                        type="button"
                        onClick={handleUpload}
                        disabled={isUploading}
                        className="btn-gold px-5 py-2 rounded-xl text-xs font-bold inline-flex items-center gap-2 shadow-lg grow sm:grow-0 justify-center"
                      >
                        {isUploading ? (
                          <>
                            <Loader2 size={14} className="animate-spin" />
                            Uploading &amp; Scoring…
                          </>
                        ) : (
                          <>
                            <Upload size={14} />
                            Upload &amp; Analyze ({stagedImages.length})
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                )}

                {/* Staged cards grid */}
                {stagedImages.length > 0 && (
                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 pt-2">
                    {stagedImages.map((img) => (
                      <ImageCard
                        key={img.id}
                        image={img}
                        onRemove={handleRemoveStaged}
                        onPreview={setSelectedPreviewImage}
                        disabled={isUploading}
                      />
                    ))}
                  </div>
                )}
              </div>

              {/* Right Col: Info / Instructions */}
              <div className="glass-gold rounded-2xl p-6 space-y-4 border border-[var(--border-1)]">
                <p className="text-xs font-bold tracking-[0.15em] uppercase text-[var(--gold-1)]">
                  Pipeline Intelligence
                </p>
                {[
                  "Automated resolution & aspect ratio checks",
                  "SHA-256 cryptographic duplicate detection",
                  "Quality assessment (sharpness, lighting, blur)",
                  "EXIF orientation & metadata normalization",
                  "High-fidelity thumbnail generation",
                ].map((item) => (
                  <div key={item} className="flex items-start gap-2.5">
                    <CheckCircle2 size={14} className="text-[var(--gold-1)] mt-0.5 shrink-0" />
                    <span className="text-xs text-[var(--text-2)]">{item}</span>
                  </div>
                ))}

                {activeProject && (
                  <div className="mt-6 pt-5 border-t border-[var(--border-1)] space-y-2">
                    <p className="text-[10px] font-bold uppercase tracking-wider text-[var(--text-3)]">
                      Current Active Project
                    </p>
                    <p className="text-sm font-bold text-[var(--text-1)] truncate">
                      {activeProject.name}
                    </p>
                    <div className="flex items-center justify-between text-xs text-[var(--text-2)] font-mono">
                      <span>ID: #{activeProject.id.slice(-8)}</span>
                      <span className="badge badge-gold">{activeProject.image_count} photos</span>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Uploaded Photos Gallery (if project exists) */}
            {uploadedImages.length > 0 && (
              <div className="pt-8 border-t border-[var(--border-1)] space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-bold font-display text-[var(--text-1)]">
                    Uploaded Gallery ({uploadedImages.length})
                  </h3>
                  <button
                    onClick={() => setCurrentPhase(2)}
                    className="btn-gold px-5 py-2 rounded-xl text-xs font-bold flex items-center gap-2 shadow-lg"
                  >
                    <span>Proceed to Scene Understanding</span>
                    <ArrowRight size={14} />
                  </button>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                  {uploadedImages.map((img) => (
                    <div
                      key={img.id}
                      onClick={() => setSelectedPreviewImage(img)}
                      className="glass-gold rounded-2xl overflow-hidden cursor-pointer card-hover border border-[var(--border-1)]"
                    >
                      <div className="relative aspect-video bg-[var(--bg-0)]">
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img
                          src={img.thumbnail_url || img.file_url || ""}
                          alt={img.original_filename}
                          className="w-full h-full object-cover"
                        />
                        <div className="absolute top-2 left-2">
                          <span className="badge badge-success text-[10px]">Uploaded</span>
                        </div>
                      </div>
                      <div className="p-3 bg-[var(--bg-card)]">
                        <p className="text-xs font-semibold text-[var(--text-1)] truncate">
                          {img.original_filename}
                        </p>
                        <p className="text-[10px] text-[var(--text-3)] font-mono mt-0.5">
                          {img.width} × {img.height}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── PHASE 2: SCENE UNDERSTANDING ── */}
        {currentPhase === 2 && activeProject && (
          <SceneResultsView
            project={activeProject}
            images={activeProject.images}
            onAnalyzeAll={handleAnalyzeAll}
            onUpdateScene={handleUpdateScene}
            onReanalyzeImage={handleReanalyzeImage}
            onInspectImage={(img) => setSelectedPreviewImage(img)}
            onBackToUpload={() => setCurrentPhase(1)}
            onProceedToPhase3={() => setIsNextPhaseModalOpen(true)}
            isAnalyzing={isAnalyzing}
          />
        )}

        {/* Phase 2 Fallback if no project */}
        {currentPhase === 2 && !activeProject && (
          <div className="glass-gold rounded-3xl p-16 text-center max-w-lg mx-auto border border-[var(--border-2)] space-y-4">
            <AlertCircle size={36} className="text-[var(--gold-1)] mx-auto" />
            <h3 className="font-display text-xl font-bold text-[var(--text-1)]">No Project Initialized</h3>
            <p className="text-xs text-[var(--text-2)] leading-relaxed">
              Upload your property photos in Phase 1 first to create a project session and begin scene understanding.
            </p>
            <button
              onClick={() => setCurrentPhase(1)}
              className="btn-gold px-6 py-2.5 rounded-xl text-xs font-bold"
            >
              ← Return to Upload
            </button>
          </div>
        )}

        {/* ── PHASE 3: WALKTHROUGH PLANNING ── */}
        {currentPhase === 3 && activeProject && currentPlan && (
          <WalkthroughPlanView
            project={activeProject}
            plan={currentPlan}
            onSavePlan={handleSavePlan}
            onRebuildPlan={handleRebuildPlan}
            onInspectImage={handleInspectByImageId}
            onBackToScenes={() => setCurrentPhase(2)}
            onProceedToPhase4={() => setCurrentPhase(4)}
            isSaving={isSavingPlan}
            isRebuilding={isRebuildingPlan}
          />
        )}

        {/* Phase 3 Loading */}
        {currentPhase === 3 && isLoadingPlan && (
          <div className="flex flex-col items-center justify-center py-24 space-y-4">
            <Loader2 size={32} className="animate-spin text-[var(--gold-1)]" />
            <p className="text-sm font-medium text-[var(--text-2)]">Generating cinematic walkthrough route…</p>
          </div>
        )}

        {/* ── PHASE 4: VIDEO GENERATION ── */}
        {currentPhase === 4 && activeProject && (
          <GenerationView
            projectId={activeProject.id}
            onBackToPlan={() => setCurrentPhase(3)}
          />
        )}

        {/* Phase 4 Fallback if no project */}
        {currentPhase === 4 && !activeProject && (
          <div className="glass-gold rounded-3xl p-16 text-center max-w-lg mx-auto border border-[var(--border-2)] space-y-4">
            <Film size={36} className="text-[var(--gold-1)] mx-auto" />
            <h3 className="font-display text-xl font-bold text-[var(--text-1)]">No Active Walkthrough</h3>
            <p className="text-xs text-[var(--text-2)] leading-relaxed">
              Complete walkthrough planning in Phase 3 before generating video clips.
            </p>
            <button
              onClick={() => setCurrentPhase(1)}
              className="btn-gold px-6 py-2.5 rounded-xl text-xs font-bold"
            >
              ← Start at Phase 1
            </button>
          </div>
        )}
      </main>

      {/* ── Modals ── */}
      {selectedPreviewImage && (
        <ImagePreviewModal
          image={selectedPreviewImage}
          onClose={() => setSelectedPreviewImage(null)}
        />
      )}

      {isNextPhaseModalOpen && (
        <NextPhaseModal
          isOpen={isNextPhaseModalOpen}
          onClose={() => {
            setIsNextPhaseModalOpen(false);
            setCurrentPhase(3);
          }}
          project={activeProject}
        />
      )}
    </div>
  );
}
