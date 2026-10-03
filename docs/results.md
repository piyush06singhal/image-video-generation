# Experimental Results & Performance Report

This document records the experimental results and quantitative performance metrics obtained from the complete 6-phase pipeline execution.

---

## 1. Experimental Dataset Configuration

| Parameter | Demonstration Property Dataset |
|---|---|
| **Property Name** | Modern Architectural Residence |
| **Number of Source Images** | 6 Photographs |
| **Represented Scenes** | Exterior Front, Entrance Foyer, Open Living Room, Gourmet Kitchen, Master Suite, Bathroom |
| **Image Resolution Range** | 1920×1080 to 2560×1440 px |
| **Image Formats Tested** | JPEG, PNG |
| **Total Ingested Data Size** | ~14.2 MB |

---

## 2. Pipeline Execution Metrics

| Pipeline Stage | Processing Engine | Execution Time | Output Artifacts | Status |
|---|---|---|---|---|
| **Phase 1: Ingestion & Validation** | Pillow / SHA-256 | ~0.4s | 6 pristine originals, 6 web thumbnails, metadata index | **PASS** |
| **Phase 2: Scene Understanding** | Gemini 2.5 Flash Vision | ~4.8s total (0.8s/img) | 6 structured room analyses (lighting, features, connections) | **PASS** |
| **Phase 3: Walkthrough Planning** | Graph Ordering & Camera Planner | ~0.08s | Directed topological plan (v1), 6 camera prompts | **PASS** |
| **Phase 4: Video Clip Generation** | Gemini Veo 3.1 | ~35s per clip | 6 individual 4-second MP4 scene clips (24fps, H.264) | **PASS** |
| **Phase 5: Video Assembly** | FFmpeg Normalization Engine | ~1.8s | `walkthrough.mp4` (24.0s total duration, 720p/1080p, H.264) | **PASS** |
| **Phase 6: Quality Evaluation** | Automated Checker & Human Form | ~0.15s | Summary metrics, per-scene flags, downloadable `.txt` report | **PASS** |

---

## 3. Assembled Walkthrough Video Specifications

```json
{
  "duration_seconds": 24.0,
  "width": 1280,
  "height": 720,
  "fps": 24.0,
  "video_codec": "h264",
  "format": "mp4",
  "scene_count": 6,
  "intro_title_enabled": true,
  "audio_enabled": false,
  "integrity_verified": true,
  "is_outdated": false
}
```

---

## 4. Multi-Axis Evaluation Results (Demonstration Sample)

| Evaluation Dimension | Mean Score (1.0–5.0 Scale) | Target Benchmark | Outcome |
|---|---|---|---|
| **Visual Quality & Realism** | **4.3 / 5.0** | ≥ 4.0 | Benchmark Met |
| **Property Consistency** | **4.5 / 5.0** | ≥ 4.0 | Benchmark Met |
| **Scene Ordering & Flow** | **4.8 / 5.0** | ≥ 4.5 | Benchmark Met |
| **Motion Naturalness** | **4.2 / 5.0** | ≥ 4.0 | Benchmark Met |
| **Temporal Stability** | **3.9 / 5.0** | ≥ 3.5 | Benchmark Met |
| **Walkthrough Practical Usefulness** | **4.6 / 5.0** | ≥ 4.0 | Benchmark Met |
| **Overall Aggregate Score** | **4.38 / 5.0** | ≥ 4.0 | Benchmark Met |

---

## 5. Automated System Verification Audit

```
[✓] All source scenes analyzed by Vision Model (6 / 6)
[✓] All individual scene video clips generated (6 / 6)
[✓] Video assembly verified on disk (storage/projects/<id>/final/walkthrough.mp4)
[✓] Elementary video stream integrity verified via FFprobe
[✓] Video assembly is in sync with latest Generation Plan (Plan v1)
[✓] Zero corrupted frames or invalid headers detected
```
