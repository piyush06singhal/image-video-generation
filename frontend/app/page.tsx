"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Header } from "@/components/Header";
import { PhaseTracker } from "@/components/PhaseTracker";
import { PropertyForm } from "@/components/PropertyForm";
import { Dropzone } from "@/components/Dropzone";
import { ImageGrid } from "@/components/ImageGrid";
import { SceneResultsView } from "@/components/SceneResultsView";
import { AlertBanner, AlertType } from "@/components/AlertBanner";
import { ImagePreviewModal } from "@/components/ImagePreviewModal";
import { NextPhaseModal } from "@/components/NextPhaseModal";
import { ImageMetadata, StagedImage } from "@/types/image";
import { Project } from "@/types/project";
import { SceneType } from "@/types/scene";
import { api, ApiError } from "@/lib/api";
import { extractLocalImageDimensions, generateClientId } from "@/lib/utils";
import { ArrowRight, Brain, Sparkles, Layers, ShieldCheck } from "lucide-react";

export default function Home() {
  const [currentPhase, setCurrentPhase] = useState<number>(1);
  const [propertyName, setPropertyName] = useState<string>("Modern 3BHK Apartment");
  const [stagedImages, setStagedImages] = useState<StagedImage[]>([]);
  const [activeProject, setActiveProject] = useState<Project | null>(null);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [isBackendHealthy, setIsBackendHealthy] = useState<boolean | null>(null);
  const [isCheckingHealth, setIsCheckingHealth] = useState<boolean>(false);
  const [alert, setAlert] = useState<{
    type: AlertType;
    title?: string;
    message: string;
  } | null>(null);
  const [selectedPreviewImage, setSelectedPreviewImage] = useState<
    ImageMetadata | StagedImage | null
  >(null);
  const [isNextPhaseModalOpen, setIsNextPhaseModalOpen] = useState<boolean>(false);

  // Check Backend Health on Mount
  const checkHealth = useCallback(async () => {
    setIsCheckingHealth(true);
    try {
      const res = await api.checkHealth();
      if (res && res.status === "healthy") {
        setIsBackendHealthy(true);
      } else {
        setIsBackendHealthy(false);
      }
    } catch {
      setIsBackendHealthy(false);
    } finally {
      setIsCheckingHealth(false);
    }
  }, []);

  useEffect(() => {
    checkHealth();
  }, [checkHealth]);

  // Handle Local File Selection from Dropzone
  const handleFilesSelected = async (newFiles: File[]) => {
    if (newFiles.length === 0) return;

    const allowedMimeTypes = ["image/jpeg", "image/png", "image/webp", "image/jpg"];
    const maxSizeBytes = 20 * 1024 * 1024; // 20 MB

    const processedNewImages: StagedImage[] = [];
    const invalidFiles: string[] = [];

    for (const file of newFiles) {
      const fileType = file.type.toLowerCase();
      const hasValidExt = /\.(jpg|jpeg|png|webp)$/i.test(file.name);

      if (!allowedMimeTypes.includes(fileType) && !hasValidExt) {
        invalidFiles.push(`${file.name} (unsupported format)`);
        continue;
      }

      if (file.size > maxSizeBytes) {
        invalidFiles.push(`${file.name} (exceeds 20 MB)`);
        continue;
      }

      const isAlreadyStaged = stagedImages.some(
        (img) => img.name === file.name && img.size === file.size
      );
      if (isAlreadyStaged) {
        invalidFiles.push(`${file.name} (already in list)`);
        continue;
      }

      const previewUrl = URL.createObjectURL(file);
      let dimensions: { width?: number; height?: number; aspectRatio?: number } = {};

      try {
        dimensions = await extractLocalImageDimensions(file);
      } catch {
        // Fallback
      }

      processedNewImages.push({
        id: generateClientId(),
        file,
        previewUrl,
        name: file.name,
        size: file.size,
        width: dimensions.width,
        height: dimensions.height,
        aspectRatio: dimensions.aspectRatio,
        status: "staged",
      });
    }

    if (invalidFiles.length > 0) {
      setAlert({
        type: "warning",
        title: "Some files were skipped",
        message: invalidFiles.join(", "),
      });
    }

    if (processedNewImages.length > 0) {
      setStagedImages((prev) => [...prev, ...processedNewImages]);
    }
  };

  // Remove single image
  const handleRemoveImage = async (id: string) => {
    const target = stagedImages.find((img) => img.id === id);
    if (!target) return;

    if (target.serverData && activeProject) {
      try {
        await api.deleteImage(activeProject.id, target.serverData.id);
        const updatedProject = await api.getProject(activeProject.id);
        setActiveProject(updatedProject);
      } catch (err) {
        const message =
          err instanceof ApiError ? err.message : "Failed to delete image from backend.";
        setAlert({
          type: "error",
          title: "Delete Failed",
          message,
        });
        return;
      }
    }

    if (target.previewUrl.startsWith("blob:")) {
      URL.revokeObjectURL(target.previewUrl);
    }

    setStagedImages((prev) => prev.filter((img) => img.id !== id));
  };

  // Clear all staged/uploaded images
  const handleClearAll = async () => {
    stagedImages.forEach((img) => {
      if (img.previewUrl.startsWith("blob:")) {
        URL.revokeObjectURL(img.previewUrl);
      }
    });

    setStagedImages([]);
    setAlert(null);
  };

  // Upload & Validate Flow
  const handleUploadAndValidate = async () => {
    if (!propertyName.trim()) {
      setAlert({
        type: "error",
        title: "Property Name Required",
        message: "Please enter a valid property name before uploading images.",
      });
      return;
    }

    const unuploadedImages = stagedImages.filter((img) => img.status === "staged");
    if (unuploadedImages.length === 0) {
      setAlert({
        type: "info",
        message: "All selected images are already uploaded and validated.",
      });
      return;
    }

    setIsUploading(true);
    setAlert(null);

    setStagedImages((prev) =>
      prev.map((img) =>
        img.status === "staged" ? { ...img, status: "uploading" } : img
      )
    );

    try {
      let currentProject = activeProject;
      if (!currentProject) {
        currentProject = await api.createProject(propertyName.trim());
        setActiveProject(currentProject);
      }

      const filesToUpload = unuploadedImages.map((img) => img.file!).filter(Boolean);
      const batchResult = await api.uploadImages(currentProject.id, filesToUpload);

      const uploadedMap = new Map(
        batchResult.uploaded.map((m) => [m.original_filename, m])
      );
      const rejectedMap = new Map(
        batchResult.rejected.map((r) => [r.filename, r])
      );

      setStagedImages((prev) =>
        prev.map((img) => {
          if (img.status !== "uploading") return img;

          const matchServer = uploadedMap.get(img.name);
          if (matchServer) {
            return {
              ...img,
              status: "validated",
              width: matchServer.width,
              height: matchServer.height,
              aspectRatio: matchServer.aspect_ratio,
              serverData: matchServer,
            };
          }

          const matchReject = rejectedMap.get(img.name);
          if (matchReject) {
            return {
              ...img,
              status: "error",
              errorMessage: matchReject.message,
            };
          }

          return img;
        })
      );

      const refreshedProject = await api.getProject(currentProject.id);
      setActiveProject(refreshedProject);

      if (batchResult.total_rejected > 0) {
        setAlert({
          type: "warning",
          title: "Partial Upload Warning",
          message: `${batchResult.total_accepted} images validated. ${batchResult.total_rejected} image(s) rejected.`,
        });
      } else {
        setAlert({
          type: "success",
          title: "Validation Complete",
          message: `Successfully validated ${batchResult.total_accepted} property photographs. Ready for Scene Understanding.`,
        });
      }
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : "An unexpected error occurred during image upload.";

      setAlert({
        type: "error",
        title: "Upload Error",
        message,
      });

      setStagedImages((prev) =>
        prev.map((img) =>
          img.status === "uploading"
            ? { ...img, status: "error", errorMessage: message }
            : img
        )
      );
    } finally {
      setIsUploading(false);
    }
  };

  // Phase 2: Run Multimodal Scene Analysis
  const handleAnalyzeAll = async (forceReanalyze: boolean = false) => {
    if (!activeProject) return;

    setIsAnalyzing(true);
    setAlert(null);

    try {
      const updatedProject = await api.analyzeProject(activeProject.id, forceReanalyze);
      setActiveProject(updatedProject);

      // Sync updated server metadata with staged image cards
      const imgMap = new Map(updatedProject.images.map((img) => [img.id, img]));
      setStagedImages((prev) =>
        prev.map((staged) => {
          if (staged.serverData && imgMap.has(staged.serverData.id)) {
            const updatedMeta = imgMap.get(staged.serverData.id)!;
            return {
              ...staged,
              serverData: updatedMeta,
            };
          }
          return staged;
        })
      );

      const completedCount = updatedProject.images.filter(
        (img) => img.analysis_status === "completed"
      ).length;
      const failedCount = updatedProject.images.filter(
        (img) => img.analysis_status === "failed"
      ).length;

      if (failedCount > 0) {
        setAlert({
          type: "warning",
          title: "Analysis Partially Completed",
          message: `${completedCount} images analyzed successfully; ${failedCount} images failed analysis.`,
        });
      } else {
        setAlert({
          type: "success",
          title: "Scene Understanding Complete",
          message: `All ${completedCount} property photographs have been analyzed and classified with structured scene metadata.`,
        });
      }
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : "An unexpected error occurred during scene understanding.";

      setAlert({
        type: "error",
        title: "Scene Analysis Error",
        message,
      });
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Phase 2: Manual User Scene Correction
  const handleUpdateScene = async (imageId: string, newSceneType: SceneType) => {
    if (!activeProject) return;

    try {
      const updatedImage = await api.updateImageScene(activeProject.id, imageId, {
        scene_type: newSceneType,
      });

      // Update in active project
      setActiveProject((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          images: prev.images.map((img) => (img.id === imageId ? updatedImage : img)),
        };
      });

      // Update in staged images
      setStagedImages((prev) =>
        prev.map((staged) =>
          staged.serverData?.id === imageId
            ? { ...staged, serverData: updatedImage }
            : staged
        )
      );

      setAlert({
        type: "info",
        message: `Scene classification for ${updatedImage.original_filename} updated to "${newSceneType.replace("_", " ")}" and saved.`,
      });
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : "Failed to update scene classification.";
      setAlert({
        type: "error",
        title: "Update Failed",
        message,
      });
    }
  };

  // Phase 2: Re-analyze Single Image
  const handleReanalyzeSingle = async (imageId: string) => {
    if (!activeProject) return;

    setIsAnalyzing(true);
    setAlert(null);

    try {
      const updatedProject = await api.analyzeProject(activeProject.id, true, [imageId]);
      setActiveProject(updatedProject);

      const targetMeta = updatedProject.images.find((img) => img.id === imageId);
      if (targetMeta) {
        setStagedImages((prev) =>
          prev.map((staged) =>
            staged.serverData?.id === imageId
              ? { ...staged, serverData: targetMeta }
              : staged
          )
        );
      }

      setAlert({
        type: "success",
        title: "Image Re-analyzed",
        message: `Successfully re-analyzed ${targetMeta?.original_filename || "image"}.`,
      });
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : "Failed to re-analyze image.";
      setAlert({
        type: "error",
        title: "Re-analysis Error",
        message,
      });
    } finally {
      setIsAnalyzing(false);
    }
  };

  const hasUnsavedChanges = stagedImages.some((img) => img.status === "staged");
  const hasValidatedImages =
    (activeProject && activeProject.images.length > 0) ||
    stagedImages.some((img) => img.status === "validated");

  return (
    <div
      className="min-h-screen flex flex-col font-sans relative"
      style={{ background: "var(--bg-deep)", color: "var(--text-primary)" }}
    >
      {/* Top Header */}
      <Header
        isBackendHealthy={isBackendHealthy}
        onRetryHealth={checkHealth}
        isCheckingHealth={isCheckingHealth}
      />

      {/* Academic Workflow Stepper */}
      <PhaseTracker
        currentPhase={currentPhase}
        onSelectPhase={(phaseId) => setCurrentPhase(phaseId)}
        hasImages={hasValidatedImages}
      />

      {/* Main Content Area */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full grow space-y-7 relative z-10">
        {/* Dynamic Alert Banner */}
        {alert && (
          <AlertBanner
            type={alert.type}
            title={alert.title}
            message={alert.message}
            onDismiss={() => setAlert(null)}
          />
        )}

        {/* Backend Offline Warning if applicable */}
        {isBackendHealthy === false && (
          <AlertBanner
            type="error"
            title="Backend Server Offline"
            message="Cannot reach the FastAPI backend at http://localhost:8000. Please ensure the backend uvicorn process is active."
          />
        )}

        {/* PHASE 1 VIEW: Upload & Ingestion */}
        {currentPhase === 1 && (
          <div className="space-y-6 animate-in fade-in duration-200">
            {/* Intro Section */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <h2 className="text-xl font-bold tracking-tight text-slate-100 flex items-center gap-2">
                  <span>Step 1: Property Image Ingestion &amp; Validation</span>
                </h2>
                <p className="text-sm text-slate-400 max-w-3xl mt-1 leading-relaxed">
                  Upload interior and exterior property photographs. Each image is verified for
                  dimensions, aspect ratio, format compliance, and exact duplicates.
                </p>
              </div>

              {hasValidatedImages && (
                <button
                  type="button"
                  onClick={() => setCurrentPhase(2)}
                  className="btn-primary px-4 py-2 text-xs font-semibold rounded-xl flex items-center gap-2 self-start"
                >
                  <span>Go to Scene Understanding</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              )}
            </div>

            {/* Property Form */}
            <PropertyForm
              propertyName={propertyName}
              onChangeName={setPropertyName}
              activeProject={activeProject}
              disabled={isUploading}
            />

            {/* Dropzone */}
            <Dropzone
              onFilesSelected={handleFilesSelected}
              disabled={isUploading || isBackendHealthy === false}
            />

            {/* Staged & Validated Image Grid */}
            <ImageGrid
              images={stagedImages}
              onRemove={handleRemoveImage}
              onClearAll={handleClearAll}
              onUpload={handleUploadAndValidate}
              onPreview={setSelectedPreviewImage}
              isUploading={isUploading}
              hasUnsavedChanges={hasUnsavedChanges}
              onContinueToPhase2={() => setCurrentPhase(2)}
            />
          </div>
        )}

        {/* PHASE 2 VIEW: Scene Understanding & Room Classification */}
        {currentPhase === 2 && (
          <div className="space-y-6 animate-in fade-in duration-200">
            {activeProject && activeProject.images.length > 0 ? (
              <SceneResultsView
                project={activeProject}
                images={activeProject.images}
                onAnalyzeAll={handleAnalyzeAll}
                onUpdateScene={handleUpdateScene}
                onReanalyzeImage={handleReanalyzeSingle}
                onInspectImage={setSelectedPreviewImage}
                onBackToUpload={() => setCurrentPhase(1)}
                onProceedToPhase3={() => setIsNextPhaseModalOpen(true)}
                isAnalyzing={isAnalyzing}
              />
            ) : (
              <div className="glass-card-elevated rounded-3xl p-12 text-center space-y-4 border border-slate-800">
                <div className="w-14 h-14 rounded-2xl bg-indigo-950/60 border border-indigo-500/30 text-indigo-400 flex items-center justify-center mx-auto shadow-[0_0_20px_rgba(99,102,241,0.2)]">
                  <Layers className="w-7 h-7" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-slate-100">
                    No Validated Photographs Available
                  </h3>
                  <p className="text-xs text-slate-400 max-w-md mx-auto mt-1.5 leading-relaxed">
                    Please upload and validate property photographs in Step 1 before proceeding to visual
                    scene understanding.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setCurrentPhase(1)}
                  className="btn-primary px-5 py-2.5 text-xs font-semibold rounded-xl"
                >
                  Return to Step 1 (Upload)
                </button>
              </div>
            )}
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/80 glass-card-elevated py-5 text-center text-xs text-slate-500 mt-auto relative z-10">
        <p className="flex items-center justify-center gap-2 flex-wrap">
          <span>AI Property Walkthrough Prototype</span>
          <span>&bull;</span>
          <span className="text-indigo-400">Phase 2: Visual Scene Understanding</span>
          <span>&bull;</span>
          <span>Academic Minor Project</span>
        </p>
      </footer>

      {/* Image Inspection Modal */}
      <ImagePreviewModal
        image={selectedPreviewImage}
        onClose={() => setSelectedPreviewImage(null)}
      />

      {/* Next Phase Transition Modal */}
      <NextPhaseModal
        isOpen={isNextPhaseModalOpen}
        onClose={() => setIsNextPhaseModalOpen(false)}
        project={activeProject}
      />
    </div>
  );
}
