"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { ImageMetadata } from "@/types/image";
import { PlannedScene } from "@/types/plan";
import { SceneReviewCreate, SceneReviewRecord, SceneReviewStatus } from "@/types/evaluation";
import { api } from "@/lib/api";
import {
  Compass,
  Maximize2,
  Minimize2,
  RotateCcw,
  Play,
  Pause,
  ZoomIn,
  ZoomOut,
  ChevronLeft,
  ChevronRight,
  Info,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Eye,
  Film,
  Image as ImageIcon,
  Check,
  RefreshCw,
  Loader2,
} from "lucide-react";

interface ImmersiveSceneViewerProps {
  projectId: string;
  scenes?: PlannedScene[];
  images?: ImageMetadata[];
  activeSceneIndex?: number;
  onSelectSceneIndex?: (index: number) => void;
  sceneReviews?: SceneReviewRecord[];
  onReviewsUpdated?: () => void;
}

const REVIEW_FLAG_OPTIONS = [
  { id: "geometry_distortion", label: "Geometry Distortion" },
  { id: "object_inconsistency", label: "Object Inconsistency" },
  { id: "flickering", label: "Flickering / Shimmer" },
  { id: "unnatural_motion", label: "Unnatural Motion Velocity" },
  { id: "lighting_drift", label: "Lighting Drift" },
];

export function ImmersiveSceneViewer({
  projectId,
  scenes: propScenes,
  images: propImages,
  activeSceneIndex: propActiveIndex,
  onSelectSceneIndex,
  sceneReviews: propReviews = [],
  onReviewsUpdated,
}: ImmersiveSceneViewerProps) {
  // Internal state when props are not provided
  const [internalScenes, setInternalScenes] = useState<PlannedScene[]>(propScenes || []);
  const [internalImages, setInternalImages] = useState<ImageMetadata[]>(propImages || []);
  const [internalReviews, setInternalReviews] = useState<SceneReviewRecord[]>(propReviews);
  const [internalActiveIndex, setInternalActiveIndex] = useState(propActiveIndex ?? 0);
  const [loadingInternal, setLoadingInternal] = useState(false);

  const fetchInternalData = useCallback(async () => {
    if (propScenes && propScenes.length > 0 && propImages && propImages.length > 0) return;
    setLoadingInternal(true);
    try {
      const [planRes, imgRes, reviewsRes] = await Promise.all([
        api.getPlan(projectId).catch(() => null),
        api.getImages(projectId).catch(() => []),
        api.getSceneReviews(projectId).catch(() => []),
      ]);
      if (planRes && planRes.scenes) {
        setInternalScenes(planRes.scenes);
      }
      if (imgRes) {
        setInternalImages(imgRes);
      }
      if (reviewsRes) {
        setInternalReviews(reviewsRes);
      }
    } catch (err) {
      console.error("Failed to load immersive viewer data:", err);
    } finally {
      setLoadingInternal(false);
    }
  }, [projectId, propScenes, propImages]);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      void fetchInternalData();
    }, 0);
    return () => window.clearTimeout(timeoutId);
  }, [fetchInternalData]);

  const scenes = propScenes && propScenes.length > 0 ? propScenes : internalScenes;
  const images = propImages && propImages.length > 0 ? propImages : internalImages;
  const sceneReviews = propReviews && propReviews.length > 0 ? propReviews : internalReviews;
  const activeSceneIndex = propActiveIndex !== undefined ? propActiveIndex : internalActiveIndex;

  const handleSelectScene = (index: number) => {
    if (onSelectSceneIndex) {
      onSelectSceneIndex(index);
    } else {
      setInternalActiveIndex(index);
    }
  };

  const activeScene = scenes[activeSceneIndex] || scenes[0];
  const activeImage = images.find((img) => img.id === activeScene?.image_id);

  // View modes within the scene: "source" (photograph) or "clip" (generated video)
  const [mediaTab, setMediaTab] = useState<"source" | "clip">("source");

  // Interaction states for Normal photo pan/zoom
  const [zoom, setZoom] = useState(1.0);
  const [panOffset, setPanOffset] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const dragStartRef = useRef({ x: 0, y: 0 });
  const containerRef = useRef<HTMLDivElement | null>(null);

  // 360 Panorama WebGL / Canvas state
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [yaw, setYaw] = useState(0); // Horizontal rotation in degrees
  const [pitch, setPitch] = useState(0); // Vertical rotation in degrees
  const [fov, setFov] = useState(75); // Field of View
  const [autoRotate, setAutoRotate] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isPanoLoading, setIsPanoLoading] = useState(false);

  // Scene review flag form state
  const existingReview = sceneReviews.find((r) => r.scene_id === activeScene?.scene_id);
  const [reviewStatus, setReviewStatus] = useState<SceneReviewStatus>(existingReview?.status || "acceptable");
  const [selectedFlags, setSelectedFlags] = useState<string[]>(existingReview?.flags || []);
  const [reviewNotes, setReviewNotes] = useState(existingReview?.notes || "");
  const [isSavingReview, setIsSavingReview] = useState(false);
  const [reviewSavedSuccess, setReviewSavedSuccess] = useState(false);

  // Panorama toggle state
  const [isPanoramicLocal, setIsPanoramicLocal] = useState(Boolean(activeImage?.is_panoramic));
  const [isUpdatingPano, setIsUpdatingPano] = useState(false);

  // Sync state when active scene changes
  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      setZoom(1.0);
      setPanOffset({ x: 0, y: 0 });
      setYaw(0);
      setPitch(0);
      setFov(75);
      setAutoRotate(false);
      setIsPanoramicLocal(Boolean(activeImage?.is_panoramic));

      const rev = sceneReviews.find((r) => r.scene_id === activeScene?.scene_id);
      setReviewStatus(rev?.status || "acceptable");
      setSelectedFlags(rev?.flags || []);
      setReviewNotes(rev?.notes || "");
      setReviewSavedSuccess(false);
    }, 0);
    return () => window.clearTimeout(timeoutId);
  }, [activeSceneIndex, activeScene?.scene_id, activeImage, sceneReviews]);

  // Handle Panorama Canvas 360 Rendering
  useEffect(() => {
    if (!isPanoramicLocal || !activeImage || mediaTab !== "source") return;

    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const animId: number | null = null;
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.src = activeImage.file_url || activeImage.analysis_image_url || activeImage.thumbnail_url || "";
    setIsPanoLoading(true);

    img.onload = () => {
      setIsPanoLoading(false);
      const render = () => {
        if (!canvas || !ctx) return;
        const w = canvas.width;
        const h = canvas.height;

        // Clear canvas
        ctx.clearRect(0, 0, w, h);

        // Compute equirectangular window slicing based on yaw, pitch, FOV
        const radYaw = ((yaw % 360) + 360) % 360;
        const sourceX = (radYaw / 360) * img.width;
        const sourceY = Math.max(0, Math.min(img.height, ((pitch + 90) / 180) * img.height - (img.height * (fov / 180)) / 2));
        const sourceW = (fov / 360) * img.width;
        const sourceH = (fov / 180) * img.height;

        if (sourceX + sourceW <= img.width) {
          ctx.drawImage(img, sourceX, sourceY, sourceW, sourceH, 0, 0, w, h);
        } else {
          // Wrapped seam handling
          const part1W = img.width - sourceX;
          const part2W = sourceW - part1W;
          const targetPart1W = (part1W / sourceW) * w;
          const targetPart2W = w - targetPart1W;

          ctx.drawImage(img, sourceX, sourceY, part1W, sourceH, 0, 0, targetPart1W, h);
          ctx.drawImage(img, 0, sourceY, part2W, sourceH, targetPart1W, 0, targetPart2W, h);
        }
      };

      render();
    };

    return () => {
      if (animId !== null) {
        cancelAnimationFrame(animId);
      }
    };
  }, [isPanoramicLocal, activeImage, mediaTab, yaw, pitch, fov]);

  // Auto rotate loop for 360 view
  useEffect(() => {
    if (!autoRotate || !isPanoramicLocal || mediaTab !== "source") return;
    const interval = setInterval(() => {
      setYaw((prev) => (prev + 0.35) % 360);
    }, 30);
    return () => clearInterval(interval);
  }, [autoRotate, isPanoramicLocal, mediaTab]);

  // Mouse / Touch handlers for dragging
  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    dragStartRef.current = { x: e.clientX, y: e.clientY };
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return;
    const dx = e.clientX - dragStartRef.current.x;
    const dy = e.clientY - dragStartRef.current.y;
    dragStartRef.current = { x: e.clientX, y: e.clientY };

    if (isPanoramicLocal && mediaTab === "source") {
      // Rotate 360 Spherical View
      const sensitivity = 0.25 * (fov / 75);
      setYaw((prev) => (prev - dx * sensitivity + 360) % 360);
      setPitch((prev) => Math.max(-60, Math.min(60, prev - dy * sensitivity)));
    } else {
      // 2D Pan for normal photo
      setPanOffset((prev) => ({
        x: prev.x + dx,
        y: prev.y + dy,
      }));
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  // Wheel zoom handler
  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    if (isPanoramicLocal && mediaTab === "source") {
      setFov((prev) => Math.max(35, Math.min(110, prev + e.deltaY * 0.05)));
    } else {
      const zoomFactor = e.deltaY < 0 ? 1.15 : 0.85;
      setZoom((prev) => Math.max(1.0, Math.min(4.0, prev * zoomFactor)));
    }
  };

  // Reset View
  const handleResetView = () => {
    setZoom(1.0);
    setPanOffset({ x: 0, y: 0 });
    setYaw(0);
    setPitch(0);
    setFov(75);
    setAutoRotate(false);
  };

  // Toggle Fullscreen
  const toggleFullscreen = () => {
    if (!containerRef.current) return;
    if (!document.fullscreenElement) {
      containerRef.current.requestFullscreen().then(() => setIsFullscreen(true)).catch(() => {});
    } else {
      document.exitFullscreen().then(() => setIsFullscreen(false)).catch(() => {});
    }
  };

  // Save Scene Quality Review
  const handleSaveReview = async () => {
    if (!activeScene) return;
    setIsSavingReview(true);
    setReviewSavedSuccess(false);

    try {
      const payload: SceneReviewCreate = {
        scene_id: activeScene.scene_id,
        status: reviewStatus,
        flags: reviewStatus === "acceptable" ? [] : selectedFlags,
        notes: reviewNotes.trim() || undefined,
      };

      await api.submitSceneReview(projectId, payload);
      setReviewSavedSuccess(true);
      if (onReviewsUpdated) {
        onReviewsUpdated();
      } else {
        const updated = await api.getSceneReviews(projectId);
        setInternalReviews(updated);
      }
      setTimeout(() => setReviewSavedSuccess(false), 3000);
    } catch (err) {
      console.error("Failed to save scene review:", err);
    } finally {
      setIsSavingReview(false);
    }
  };

  // Toggle Panorama Override
  const handleTogglePanoramaOverride = async () => {
    if (!activeImage) return;
    setIsUpdatingPano(true);
    const newStatus = !isPanoramicLocal;
    setIsPanoramicLocal(newStatus);

    try {
      await api.updateImagePanorama(projectId, activeImage.id, newStatus, "equirectangular");
    } catch (err) {
      console.error("Failed to update panorama status:", err);
      setIsPanoramicLocal(!newStatus);
    } finally {
      setIsUpdatingPano(false);
    }
  };

  if (loadingInternal || !activeScene) {
    return (
      <div className="glass rounded-3xl p-16 text-center space-y-4 border border-[var(--border-1)]">
        <Loader2 className="w-8 h-8 text-[var(--gold-1)] animate-spin mx-auto" />
        <p className="text-xs text-[var(--text-3)] font-mono">Loading immersive scene data...</p>
      </div>
    );
  }

  const sceneClipDownloadUrl = api.getSceneClipDownloadUrl(projectId, activeScene.scene_id);

  return (
    <div className="space-y-6">
      {/* Disclaimer Banner - Mandatory Scope Statement */}
      <div className="p-3.5 rounded-2xl bg-[var(--bg-1)] border border-[var(--border-1)] flex items-start gap-3">
        <Info className="w-4 h-4 text-[var(--gold-1)] shrink-0 mt-0.5" />
        <div className="text-xs text-[var(--text-2)] leading-relaxed">
          <strong className="text-[var(--text-1)] font-semibold">Immersive Scene Inspector:</strong>{" "}
          Interactive spherical viewing is available only for detected equirectangular panoramas; ordinary photos use pan/zoom.{" "}
          <span className="text-[var(--text-3)] italic">
            *Immersive view is based on supplied 2D photographs and does not represent a full 3D reconstruction.
          </span>
        </div>
      </div>

      {/* Main Interactive Stage Container */}
      <div
        ref={containerRef}
        className={`glass rounded-3xl border border-[var(--border-2)] overflow-hidden shadow-2xl relative bg-black flex flex-col ${
          isFullscreen ? "fixed inset-0 z-50 rounded-none" : "min-h-[520px] aspect-video sm:min-h-[580px]"
        }`}
      >
        {/* Top Control Bar overlay */}
        <div className="absolute top-0 inset-x-0 z-20 p-4 bg-gradient-to-b from-black/80 via-black/40 to-transparent flex items-center justify-between text-white pointer-events-auto">
          {/* Scene Label & Badges */}
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-xl bg-[var(--gold-1)]/20 border border-[var(--gold-1)]/40 flex items-center justify-center font-bold text-xs text-[var(--gold-1)] font-display">
              {String((activeScene.order ?? activeSceneIndex) + 1).padStart(2, "0")}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-bold tracking-tight text-white">{activeScene.label}</span>
                {isPanoramicLocal ? (
                  <span className="badge badge-gold text-[10px] font-mono">
                    <Compass className="w-3 h-3 inline mr-1" /> 360° Panorama
                  </span>
                ) : (
                  <span className="badge text-[10px] font-mono bg-white/10 text-white/80 border border-white/20">
                    High-Res 2D Photo
                  </span>
                )}
              </div>
              <span className="text-[11px] text-white/60 capitalize">
                {activeScene.scene_type.replace(/_/g, " ")} · Camera: {activeScene.camera?.motion_type?.replace(/_/g, " ") || "Controlled Movement"}
              </span>
            </div>
          </div>

          {/* Media Switcher: Source Photo vs Generated Clip */}
          <div className="flex items-center gap-2">
            <div className="bg-black/60 backdrop-blur-md rounded-xl p-1 border border-white/20 flex items-center gap-1 text-xs">
              <button
                onClick={() => setMediaTab("source")}
                className={`px-3 py-1 rounded-lg font-semibold transition-all flex items-center gap-1.5 ${
                  mediaTab === "source"
                    ? "bg-[var(--gold-1)] text-black shadow"
                    : "text-white/70 hover:text-white"
                }`}
              >
                <ImageIcon className="w-3.5 h-3.5" />
                Source Photo
              </button>
              <button
                onClick={() => setMediaTab("clip")}
                className={`px-3 py-1 rounded-lg font-semibold transition-all flex items-center gap-1.5 ${
                  mediaTab === "clip"
                    ? "bg-[var(--gold-1)] text-black shadow"
                    : "text-white/70 hover:text-white"
                }`}
              >
                <Film className="w-3.5 h-3.5" />
                Generated Clip
              </button>
            </div>

            <button
              onClick={toggleFullscreen}
              className="p-2 bg-black/60 backdrop-blur-md hover:bg-black/80 rounded-xl border border-white/20 text-white/80 hover:text-white transition-colors"
              title="Toggle Fullscreen"
            >
              {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
            </button>
          </div>
        </div>

        {/* Viewport Canvas / Video Stage */}
        <div
          className="flex-1 relative overflow-hidden flex items-center justify-center cursor-grab active:cursor-grabbing select-none"
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          onWheel={handleWheel}
        >
          {mediaTab === "source" ? (
            isPanoramicLocal ? (
              // 360° Spherical Panoramic Canvas
              <div className="w-full h-full relative flex items-center justify-center">
                <canvas
                  ref={canvasRef}
                  width={1280}
                  height={720}
                  className="w-full h-full object-cover"
                />
                {isPanoLoading && (
                  <div className="absolute inset-0 flex items-center justify-center bg-black/50 text-white text-xs gap-2">
                    <RefreshCw className="w-4 h-4 animate-spin text-[var(--gold-1)]" />
                    <span>Loading 360° spherical projection...</span>
                  </div>
                )}
              </div>
            ) : (
              // High-Res 2D Pan/Zoom Photograph
              <div
                className="w-full h-full flex items-center justify-center transition-transform duration-75"
                style={{
                  transform: `translate(${panOffset.x}px, ${panOffset.y}px) scale(${zoom})`,
                  transformOrigin: "center center",
                }}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={activeImage?.file_url || activeImage?.analysis_image_url || activeImage?.thumbnail_url || ""}
                  alt={activeScene.label}
                  className="max-w-full max-h-full object-contain pointer-events-none"
                  draggable={false}
                />
              </div>
            )
          ) : (
            // Generated Scene Clip Player
            <div className="w-full h-full flex items-center justify-center bg-black">
              <video
                src={sceneClipDownloadUrl}
                controls
                autoPlay
                loop
                playsInline
                className="w-full h-full object-contain"
              />
            </div>
          )}

          {/* Quick HUD Overlay Controls (Bottom Right) */}
          {mediaTab === "source" && (
            <div className="absolute bottom-5 right-5 z-20 flex items-center gap-2 bg-black/70 backdrop-blur-md px-3 py-1.5 rounded-2xl border border-white/20 text-white">
              {isPanoramicLocal ? (
                <>
                  <button
                    onClick={() => setAutoRotate(!autoRotate)}
                    className={`p-1.5 rounded-lg text-xs font-semibold flex items-center gap-1 transition-colors ${
                      autoRotate ? "text-[var(--gold-1)] bg-white/10" : "text-white/70 hover:text-white"
                    }`}
                    title="Auto-Rotate 360°"
                  >
                    {autoRotate ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
                    <span className="text-[10px] hidden sm:inline">Auto-Turn</span>
                  </button>

                  <div className="h-4 w-px bg-white/20" />

                  <button
                    onClick={() => setFov((prev) => Math.max(35, prev - 8))}
                    className="p-1 hover:text-[var(--gold-1)]"
                    title="Zoom In (FOV)"
                  >
                    <ZoomIn className="w-4 h-4" />
                  </button>
                  <span className="text-[10px] font-mono text-white/60 w-8 text-center">{Math.round(fov)}°</span>
                  <button
                    onClick={() => setFov((prev) => Math.min(110, prev + 8))}
                    className="p-1 hover:text-[var(--gold-1)]"
                    title="Zoom Out (FOV)"
                  >
                    <ZoomOut className="w-4 h-4" />
                  </button>
                </>
              ) : (
                <>
                  <button
                    onClick={() => setZoom((prev) => Math.min(4.0, prev * 1.25))}
                    className="p-1 hover:text-[var(--gold-1)]"
                    title="Zoom In"
                  >
                    <ZoomIn className="w-4 h-4" />
                  </button>
                  <span className="text-[10px] font-mono text-white/60 w-9 text-center">
                    {zoom.toFixed(1)}x
                  </span>
                  <button
                    onClick={() => setZoom((prev) => Math.max(1.0, prev * 0.8))}
                    className="p-1 hover:text-[var(--gold-1)]"
                    title="Zoom Out"
                  >
                    <ZoomOut className="w-4 h-4" />
                  </button>
                </>
              )}

              <div className="h-4 w-px bg-white/20" />

              <button
                onClick={handleResetView}
                className="p-1 hover:text-[var(--gold-1)] transition-colors"
                title="Reset View"
              >
                <RotateCcw className="w-3.5 h-3.5" />
              </button>
            </div>
          )}
        </div>

        {/* Bottom Scene Stepper Strip */}
        <div className="p-3 bg-black/90 border-t border-white/10 flex items-center justify-between z-20">
          <button
            onClick={() => handleSelectScene(Math.max(0, activeSceneIndex - 1))}
            disabled={activeSceneIndex === 0}
            className="btn-ghost px-3 py-1.5 rounded-xl text-xs text-white disabled:opacity-30 flex items-center gap-1"
          >
            <ChevronLeft className="w-4 h-4" />
            Previous Scene
          </button>

          {/* Scene Dots / Mini Selector */}
          <div className="flex items-center gap-2 overflow-x-auto max-w-[60%] px-2">
            {scenes.map((sc, idx) => (
              <button
                key={sc.scene_id}
                onClick={() => handleSelectScene(idx)}
                className={`px-3 py-1 rounded-xl text-xs font-semibold whitespace-nowrap transition-all flex items-center gap-1.5 ${
                  idx === activeSceneIndex
                    ? "bg-[var(--gold-1)] text-black font-bold shadow-md"
                    : "bg-white/10 text-white/70 hover:bg-white/20 hover:text-white"
                }`}
              >
                <span>{idx + 1}.</span>
                <span className="max-w-[90px] truncate">{sc.label}</span>
              </button>
            ))}
          </div>

          <button
            onClick={() => handleSelectScene(Math.min(scenes.length - 1, activeSceneIndex + 1))}
            disabled={activeSceneIndex === scenes.length - 1}
            className="btn-ghost px-3 py-1.5 rounded-xl text-xs text-white disabled:opacity-30 flex items-center gap-1"
          >
            Next Scene
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Dual Panel: Scene Metadata & Human Quality Review */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left 6 Cols: Scene Inspection & Projection Settings */}
        <div className="lg:col-span-6 glass rounded-2xl p-6 border border-[var(--border-1)] space-y-4">
          <div className="flex items-center justify-between border-b border-[var(--border-1)] pb-3">
            <h4 className="text-sm font-bold font-display text-[var(--text-1)] flex items-center gap-2">
              <Eye className="w-4 h-4 text-[var(--gold-1)]" />
              Scene Specifications & Projection
            </h4>
            <span className="badge badge-gold font-mono text-[10px]">
              Scene ID: {activeScene?.scene_id.slice(0, 8)}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="p-3 bg-[var(--bg-0)] rounded-xl border border-[var(--border-1)] space-y-0.5">
              <span className="text-[10px] text-[var(--text-3)] uppercase font-bold tracking-wider">Scene Label</span>
              <p className="font-semibold text-[var(--text-1)] truncate">{activeScene?.label}</p>
            </div>

            <div className="p-3 bg-[var(--bg-0)] rounded-xl border border-[var(--border-1)] space-y-0.5">
              <span className="text-[10px] text-[var(--text-3)] uppercase font-bold tracking-wider">Room Type</span>
              <p className="font-semibold text-[var(--text-1)] capitalize">
                {activeScene?.scene_type.replace(/_/g, " ")}
              </p>
            </div>

            <div className="p-3 bg-[var(--bg-0)] rounded-xl border border-[var(--border-1)] space-y-0.5">
              <span className="text-[10px] text-[var(--text-3)] uppercase font-bold tracking-wider">Camera Motion</span>
              <p className="font-semibold text-[var(--gold-2)] font-mono">
                {activeScene?.camera?.motion_type?.replace(/_/g, " ") || "Controlled Movement"}
              </p>
            </div>

            <div className="p-3 bg-[var(--bg-0)] rounded-xl border border-[var(--border-1)] space-y-0.5">
              <span className="text-[10px] text-[var(--text-3)] uppercase font-bold tracking-wider">Resolution</span>
              <p className="font-semibold text-[var(--text-1)] font-mono">
                {activeImage ? `${activeImage.width} × ${activeImage.height} px` : "1080p HD"}
              </p>
            </div>
          </div>

          {/* Panorama Classification Override */}
          <div className="pt-2 border-t border-[var(--border-1)] flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-[var(--text-1)]">360° Panoramic Mode</p>
              <p className="text-[11px] text-[var(--text-3)]">
                Toggle if this image is a 2:1 equirectangular spherical panorama.
              </p>
            </div>
            <button
              type="button"
              onClick={handleTogglePanoramaOverride}
              disabled={isUpdatingPano}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all ${
                isPanoramicLocal
                  ? "btn-gold"
                  : "btn-ghost"
              }`}
            >
              {isUpdatingPano ? (
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
              ) : isPanoramicLocal ? (
                "✓ 360° Panorama"
              ) : (
                "Standard Photo"
              )}
            </button>
          </div>
        </div>

        {/* Right 6 Cols: Human Scene Quality Review Box */}
        <div className="lg:col-span-6 glass-gold rounded-2xl p-6 border border-[var(--border-2)] space-y-4">
          <div className="flex items-center justify-between border-b border-[var(--border-1)] pb-3">
            <h4 className="text-sm font-bold text-[var(--text-1)] flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-[var(--gold-1)]" />
              Reviewer Scene Quality Flag
            </h4>
            <span className="text-[10px] uppercase font-bold tracking-wider text-[var(--gold-2)]">Human Review</span>
          </div>

          {/* Quality Status Selector */}
          <div className="grid grid-cols-3 gap-2.5">
            <button
              type="button"
              onClick={() => setReviewStatus("acceptable")}
              className={`p-2.5 rounded-xl border text-xs font-bold flex items-center justify-center gap-1.5 transition-all ${
                reviewStatus === "acceptable"
                  ? "bg-emerald-600 text-white border-emerald-600 shadow-md"
                  : "bg-[var(--bg-card)] border-[var(--border-1)] text-[var(--text-2)] hover:border-emerald-500/40"
              }`}
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Acceptable</span>
            </button>

            <button
              type="button"
              onClick={() => setReviewStatus("needs_review")}
              className={`p-2.5 rounded-xl border text-xs font-bold flex items-center justify-center gap-1.5 transition-all ${
                reviewStatus === "needs_review"
                  ? "bg-amber-500 text-black border-amber-500 shadow-md"
                  : "bg-[var(--bg-card)] border-[var(--border-1)] text-[var(--text-2)] hover:border-amber-500/40"
              }`}
            >
              <AlertTriangle className="w-3.5 h-3.5" />
              <span>Needs Review</span>
            </button>

            <button
              type="button"
              onClick={() => setReviewStatus("failed")}
              className={`p-2.5 rounded-xl border text-xs font-bold flex items-center justify-center gap-1.5 transition-all ${
                reviewStatus === "failed"
                  ? "bg-red-600 text-white border-red-600 shadow-md"
                  : "bg-[var(--bg-card)] border-[var(--border-1)] text-[var(--text-2)] hover:border-red-500/40"
              }`}
            >
              <XCircle className="w-3.5 h-3.5" />
              <span>Failed</span>
            </button>
          </div>

          {/* Defect / Quality Issue Checkboxes if flagged */}
          {reviewStatus !== "acceptable" && (
            <div className="space-y-2 pt-1 anim-fade-down">
              <p className="text-[11px] font-bold text-[var(--text-2)] uppercase tracking-wider">
                Flag Observed Issues:
              </p>
              <div className="flex flex-wrap gap-2">
                {REVIEW_FLAG_OPTIONS.map((opt) => {
                  const isChecked = selectedFlags.includes(opt.id);
                  return (
                    <button
                      key={opt.id}
                      type="button"
                      onClick={() =>
                        setSelectedFlags((prev) =>
                          isChecked ? prev.filter((f) => f !== opt.id) : [...prev, opt.id]
                        )
                      }
                      className={`px-3 py-1 rounded-lg text-xs font-medium border transition-all ${
                        isChecked
                          ? "bg-red-950/20 text-red-600 border-red-500/40 font-bold"
                          : "bg-[var(--bg-0)] text-[var(--text-3)] border-[var(--border-1)] hover:border-[var(--border-2)]"
                      }`}
                    >
                      {isChecked ? "✓ " : "+ "}
                      {opt.label}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Reviewer Notes */}
          <div className="space-y-1">
            <label className="text-[11px] text-[var(--text-3)] font-semibold">Reviewer Notes</label>
            <input
              type="text"
              value={reviewNotes}
              onChange={(e) => setReviewNotes(e.target.value)}
              placeholder="e.g. Sharp doorway transition, minor shadow flicker..."
              className="w-full px-3.5 py-2 rounded-xl text-xs bg-[var(--bg-card)] border border-[var(--border-1)] text-[var(--text-1)]"
            />
          </div>

          <div className="flex items-center justify-between pt-1">
            {reviewSavedSuccess && (
              <span className="text-xs text-emerald-600 font-bold flex items-center gap-1 anim-fade-up">
                <Check className="w-3.5 h-3.5" /> Review recorded
              </span>
            )}
            {!reviewSavedSuccess && <div />}

            <button
              type="button"
              onClick={handleSaveReview}
              disabled={isSavingReview}
              className="btn-gold px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-md"
            >
              {isSavingReview ? (
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Check className="w-3.5 h-3.5" />
              )}
              <span>Save Scene Review</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
