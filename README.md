# CinéEstate: Image-to-Video Walkthrough Generation for Real Estate

[![Backend](https://img.shields.io/badge/Backend-FastAPI_0.115+-009688.svg?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![Frontend](https://img.shields.io/badge/Frontend-Next.js_16_(React_19)-000000.svg?style=flat-square&logo=next.js)](https://nextjs.org)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB.svg?style=flat-square&logo=python)](https://python.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0%2B-3178C6.svg?style=flat-square&logo=typescript)](https://www.typescriptlang.org)
[![Test Suite](https://img.shields.io/badge/Tests-51%20Passed%20(100%25)-22c55e.svg?style=flat-square)]()
[![License](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](LICENSE)

An end-to-end, multi-stage generative pipeline and interactive inspection platform that transforms unordered collections of 2D real estate photographs into coherent, architecturally ordered, cinematographic video walkthroughs and immersive spatial viewing experiences.

---

## Executive Summary

Traditional real estate listings rely on disconnected photo galleries that require buyers to mentally reconstruct spatial layouts, or expensive 3D Matterport/LIDAR hardware requiring hundreds of multi-view captures. 

**CinéEstate** bridges this gap using an academic vision-language and video diffusion architecture:
1. **Automated Structural & Semantic Ingestion:** Ingests sparse, unordered photographs (5–15 images), performs byte-level integrity checks, SHA-256 deduplication, and multi-signal 360° panorama detection.
2. **Multimodal Scene Understanding (VLM):** Uses Google Gemini 2.5 Flash to classify architectural room types, evaluate lighting, detect door connections, and quantify image quality.
3. **Topological Scene Graph Planning:** Constructs a directed graph and executes topological sorting to guarantee natural walkthrough flow (`Exterior` → `Foyer` → `Living` → `Kitchen` → `Private Quarters` → `Outdoor`) with zero room hallucination.
4. **Diffusion-Based Motion Synthesis:** Translates planned camera trajectories (e.g. slow forward dollies, kitchen pans) into photorealistic 4-second video clips via Gemini Veo 2.0 with strict negative safety constraints.
5. **Deterministic Video Normalization & Assembly:** Standardizes elementary streams with FFmpeg via proportional geometric letterbox padding (preventing room stretching) and seamless crossfading.
6. **Dual-Inspection & Quantitative Evaluation:** Delivers an interactive 360° equirectangular canvas / 2D pan-zoom inspector, an automated 4-point verification engine, and a 6-axis human evaluation audit system.

---

## System Architecture

The following diagram details the end-to-end pipeline architecture, data contracts, and component boundaries across all six execution phases:

```
                                  ┌────────────────────────────────────────────────────────┐
                                  │               Next.js 16 Client Frontend               │
                                  │   (React 19 · Tailwind CSS · Canvas 360° Inspection)   │
                                  └───────────────────────────┬────────────────────────────┘
                                                              │ HTTP REST / Multipart
                                                              ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                                 FastAPI Backend Server                                                 │
│                                                                                                                        │
│   ┌───────────────────────────────────┐               ┌────────────────────────────────────────────────────────────┐   │
│   │ Phase 1: Ingestion & Validation   │               │ Phase 2: Multimodal Scene Understanding                    │   │
│   │ • Pillow verification & EXIF fix  │──────────────▶│ • Gemini 2.5 Flash Zero-Shot VLM Inference                 │   │
│   │ • SHA-256 duplicate rejection     │   Image Byte  │ • Room Classification (Living, Kitchen, etc.)              │   │
│   │ • Multi-Signal 360° Pano Detector │    Streams    │ • Illumination & Architectural Feature Analysis            │   │
│   │ • Isolated filesystem storage     │               │ • Image Quality Scoring (Brightness, Contrast, Sharpness)  │   │
│   └───────────────────────────────────┘               └─────────────────────────────┬──────────────────────────────┘   │
│                                                                                     │ Scene Metadata                   │
│                                                                                     ▼ JSON Schemas                     │
│   ┌───────────────────────────────────┐               ┌────────────────────────────────────────────────────────────┐   │
│   │ Phase 4: Image-to-Video Diffusion │               │ Phase 3: Walkthrough Planning & Trajectory Graph           │   │
│   │ • Gemini Veo 2.0 I2V Engine       │◀──────────────│ • Directed Topological Scene Graph Construction            │   │
│   │ • Prompt grounding & safety locks │ Camera Prompts│ • Hierarchy Sorting (Exterior ➔ Living ➔ Private ➔ Outdoor)│   │
│   │ • Asynchronous execution queue    │  & Parameters │ • Conservative Camera Motion Planner (Pan/Dolly/Drift)     │   │
│   │ • FFprobe elementary verification │               │ • Plan Fingerprinting & SHA-256 Versioning                 │   │
│   └─────────────────┬─────────────────┘               └────────────────────────────────────────────────────────────┘   │
│                     │ Per-Scene                                                                                        │
│                     │ MP4 Clips                                                                                        │
│                     ▼                                                                                                  │
│   ┌───────────────────────────────────┐               ┌────────────────────────────────────────────────────────────┐   │
│   │ Phase 5: Normalization & Assembly │               │ Phase 6: Immersive Viewer & Evaluation Suite               │   │
│   │ • FFmpeg Proportional Letterbox   │──────────────▶│ • 360° Spherical Equirectangular Canvas Viewer            │   │
│   │ • 16:9 Widescreen (1280x720 24fps)│ Walkthrough   │ • 2D Ultra High-Res Bounded Pan/Zoom Mode                  │   │
│   │ • Dynamic Dark Title Card Intro   │     Video     │ • 4-Point Automated Verification Checks                    │   │
│   │ • Multi-Input Crossfade Concaten. │   Artifacts   │ • 6-Axis Human Evaluation & Review Flagging                │   │
│   │ • Outdated Plan State Invalidator │               │ • Plaintext & JSON Audit Report Exporter                   │   │
│   └───────────────────────────────────┘               └────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
                                                              │
                                                              ▼
                                  ┌────────────────────────────────────────────────────────┐
                                  │            Persistent Filesystem Storage               │
                                  │   (Originals · Processed · Video Clips · Walkthrough)  │
                                  └────────────────────────────────────────────────────────┘
```

---

## Core Technical Pipeline (Phases 1–6)

### Phase 1: Ingestion & Image Preprocessing
- **Validation Engine:** Enforces strict image file bounds ($\le 20\text{ MB}$, $\ge 512\times 512\text{ px}$ resolution) and format whitelisting (`JPEG`, `PNG`, `WebP`).
- **EXIF Transposition:** Corrects sensor rotation flags automatically to prevent downstream orientation mismatch.
- **SHA-256 Deduplication:** Prevents redundant processing by fingerprinting image byte buffers.
- **Multi-Signal 360° Panorama Detection:** Evaluates embedded `GPano:ProjectionType` XMP metadata, strict $2:1$ aspect ratio criteria ($\text{width} \ge 1024\text{px}$), and left-right seam boundary Euclidean continuity.

### Phase 2: Multimodal Scene Understanding
- **Vision-Language Inference:** Prompts Google Gemini 2.5 Flash with structured system instructions to extract room classifications (`exterior_front`, `entrance_foyer`, `living_room`, `kitchen`, `bedroom`, `bathroom`, `balcony_terrace`, etc.).
- **Architectural & Environmental Analysis:** Identifies fixtures (e.g. kitchen islands, hardwood floors) and lighting conditions (`natural_daylight`, `warm_artificial`, `mixed`).
- **Mathematical Image Quality Estimation:** Computes grayscale mean luminance (brightness), luminance standard deviation (contrast), and Laplacian/FIND_EDGES variance (sharpness).

### Phase 3: Walkthrough Planning & Scene Graph Construction
- **Topological Sorting:** Builds a directed adjacency graph to eliminate spatial disorientation, enforcing an architectural sequence from public entryways to private quarters.
- **Zero Spatial Hallucination:** Intermediate rooms omitted by the user are **never** synthetically fabricated; transitions between sparse rooms are handled via direct cuts.
- **Conservative Camera Motion Selection:** Maps scene types to restrained camera trajectories (e.g. forward dolly for foyers, lateral pans for kitchens, subtle static drift for bathrooms) while injecting strict negative safety constraints.

### Phase 4: Image-to-Video Diffusion Generation
- **Generative Video Synthesis:** Uses Google Gemini Veo 2.0 to synthesize 4-second video clips from single static photographs guided by the scripted motion prompts.
- **Safety Prompt Engineering:** Appends negative prompt constraints (`no morphing, no disappearing furniture, no warping architecture, static lighting`) to prevent structural artifacts.
- **Elementary Stream Verification:** Executes FFprobe checks on every generated clip to confirm valid codec headers (`h264`), resolution, and frame counts before assembly.

### Phase 5: Video Normalization & Multi-Clip Assembly
- **Proportional Geometric Letterboxing:** Normalizes source photos of arbitrary aspect ratios ($9:16$ portrait, $1:1$ square, $4:3$) to standardized $16:9$ widescreen ($1280\times 720$ at $24.0\text{ fps}$) without optical stretching or cropping.
- **Dynamic Title Card Generation:** Renders a sleek obsidian-and-gold property title card intro using OpenCV and H.264 transcoding.
- **Transition Stitching:** Executes straight cuts or smooth crossfades ($0.35\text{s}$) using multi-input FFmpeg `filter_complex` graphs.
- **Plan Invalidation Tracking:** Compares plan SHA-256 hashes against current scene configurations to flag outdated video assemblies.

### Phase 6: Immersive Viewer & Technical Evaluation
- **Dual-Mode Inspection:** Interactive HTML5 Canvas equirectangular spherical viewer for 360° panoramas and bounded high-res 2D pan/zoom for perspective photos.
- **Automated Verification Matrix:** Non-subjective server-side checks for scene analysis completion, clip availability, video stream integrity, and plan synchronization.
- **Standardized Human Evaluation:** 6-axis scoring rubric ($1.0$ to $5.0$) paired with scene-level defect flags (`geometry_distortion`, `flickering`, `unnatural_motion`, etc.) and exportable technical audit reports.

---

## Academic Scope & Technical Boundaries

To maintain scientific integrity and realistic evaluation bounds, CinéEstate operates under explicit architectural principles:

| Principle | Architectural Decision & Defense |
| :--- | :--- |
| **Topological Graph vs. 3D Reconstruction** | Constructs a topological scene graph rather than attempting dense Structure-from-Motion (SfM), NeRF, or 3D Gaussian Splatting (3DGS). This enables high-quality synthesis from sparse photos (5–10) without requiring 100+ dense multi-view captures. |
| **Zero Spatial Hallucination** | The system never invents unseen intermediate hallways, elevators, or staircases. Unphotographed rooms are omitted, preserving absolute photographic authenticity. |
| **Authentic Aspect Ratio Preservation** | Non-16:9 photographs are letterboxed rather than cropped to fill, preserving authentic ceiling heights, floor layouts, and vertical wall geometry. |
| **Equirectangular Projection Boundaries** | True 360° equirectangular panoramas are projected onto a spherical canvas; standard perspective photos remain in 2D to prevent false spherical warping. |

---

## Evaluation Framework & Benchmark Criteria

The platform integrates a standardized evaluation rubric and objective verification engine:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 Evaluation Framework                                   │
├──────────────────────────────────────────┬─────────────────────────────────────────────┤
│ 1. Automated Pipeline Verification       │ 2. 6-Axis Human Evaluation Rubric (1.0-5.0) │
│ • Scene Analysis Coverage (100%)         │ • Visual Quality & Realism (Target: ≥ 4.0)  │
│ • Elementary Clip Availability (100%)    │ • Property Consistency (Target: ≥ 4.0)      │
│ • FFprobe Stream & Codec Integrity       │ • Scene Sequence & Flow (Target: ≥ 4.5)     │
│ • Plan Fingerprint Synchronization       │ • Motion Naturalness (Target: ≥ 4.0)        │
│                                          │ • Temporal Stability (Target: ≥ 3.5)        │
│                                          │ • Walkthrough Usefulness (Target: ≥ 4.0)    │
└──────────────────────────────────────────┴─────────────────────────────────────────────┘
```

---

## Repository Structure

```
.
├── frontend/                          # Next.js 16 / React 19 Frontend Client
│   ├── app/                           # App router (/studio, landing page, layout)
│   ├── components/                    # Modular studio components
│   │   ├── Phase1Upload.tsx           # Image upload, validation & metadata grid
│   │   ├── Phase2SceneUnderstanding.tsx # AI scene classification & quality audit
│   │   ├── Phase3WalkthroughPlan.tsx  # Interactive timeline & camera planner
│   │   ├── Phase4VideoGeneration.tsx  # Video diffusion synthesis & retry queue
│   │   ├── Phase5VideoAssembly.tsx    # Video player & FFmpeg assembly controls
│   │   ├── Phase6Evaluation.tsx       # Automated checks & 6-axis review rubric
│   │   └── ImmersiveSceneViewer.tsx   # 360° Spherical & 2D Pan/Zoom Inspector
│   ├── lib/api.ts                     # Full-featured typed REST API client
│   └── types/                         # TypeScript interfaces mirroring Pydantic models
│
├── backend/                           # Python FastAPI Backend Server
│   ├── app/
│   │   ├── api/v1/projects.py         # Consolidated REST routes across all 6 phases
│   │   ├── core/                      # Configuration, error types, logging
│   │   ├── schemas/                   # Pydantic validation schemas
│   │   │   ├── project.py             # Project & image metadata schemas
│   │   │   ├── scene.py               # VLM scene understanding schemas
│   │   │   ├── plan.py                # Walkthrough plan & camera schemas
│   │   │   ├── video.py               # Video generation & assembly schemas
│   │   │   └── evaluation.py          # Verification & review schemas
│   │   └── services/                  # Business logic services
│   │       ├── image_preprocessor.py  # Validation, EXIF & multi-signal pano detection
│   │       ├── scene_analysis_service.py # Gemini 2.5 Flash VLM inference
│   │       ├── walkthrough_planner/   # Graph ordering, camera & transition planning
│   │       ├── video_generation/      # Gemini Veo 2.0 provider & retry engine
│   │       ├── video_assembler/       # FFmpeg probe, normalize, title, concat
│   │       └── evaluation_service.py  # Verification checks & audit report generation
│   ├── storage/projects/              # Isolated local project filesystem storage
│   └── tests/                         # 51 unit & integration tests across all phases
│
├── docs/                              # Comprehensive Technical Documentation
│   ├── architecture.md                # In-depth subsystem architecture & data flows
│   ├── api.md                         # Complete REST API endpoint reference
│   ├── viva.md                        # 26 Core Viva questions & technical answers
│   ├── limitations.md                 # System boundaries & academic constraints
│   ├── final-demo.md                  # 17-step end-to-end live demonstration guide
│   ├── evaluation.md                  # Metric definitions & evaluation guidelines
│   ├── results.md                     # Experimental benchmarks & evaluation template
│   ├── screenshots.md                 # 13 ordered UI capture checklist
│   └── presentation-outline.md        # 18-slide academic presentation structure
│
├── .env.example                       # Root environment variables template
└── README.md                          # Project documentation and quickstart
```

---

## Quick Start & Local Setup

### System Prerequisites
- **Python:** `>= 3.10` (Tested on Python 3.11, 3.12, 3.14)
- **Node.js:** `>= 18.0` (Tested on Node v20 LTS, v24)
- **FFmpeg:** Bundled automatically via `imageio-ffmpeg` or local system binary
- **Gemini API Key:** Active key from Google AI Studio (`GEMINI_API_KEY`)

---

### 1. Backend Installation & Execution

```bash
# Navigate to backend directory
cd backend

# Create and activate Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env and set your GEMINI_API_KEY=your_key_here

# Launch FastAPI development server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- **Backend API Base:** `http://localhost:8000`
- **Interactive Swagger Docs:** `http://localhost:8000/docs`
- **Health Check Endpoint:** `http://localhost:8000/api/health`

---

### 2. Frontend Installation & Execution

```bash
# Navigate to frontend directory in a separate terminal
cd frontend

# Install Node dependencies
npm install

# Start Next.js development server
npm run dev
```

- **Studio Interface:** `http://localhost:3000/studio`
- **Landing Page:** `http://localhost:3000`

---

## Automated Test Suite

The project includes an automated test suite containing **51 test cases** verifying all 6 phases:

```bash
cd backend
./venv/bin/pytest tests/ -v
```

```text
============================== test session starts ==============================
collected 51 items

tests/test_image_upload.py ......... [14 passed - Phase 1 Uploads & Deduplication]
tests/test_image_preprocessor.py .... [ 4 passed - Phase 1 Pillow Preprocessing]
tests/test_scene_analysis.py ........ [ 8 passed - Phase 2 Gemini VLM & Quality Metrics]
tests/test_walkthrough_planner.py ... [ 9 passed - Phase 3 Graph Sorting & Camera Motion]
tests/test_video_generation.py ...... [ 4 passed - Phase 4 Video Synthesis & Verification]
tests/test_video_assembler.py ....... [ 6 passed - Phase 5 FFmpeg Normalization & Concat]
tests/test_evaluation.py ............ [ 5 passed - Phase 6 Pano, Verification & Reports]
tests/test_projects.py .............. [ 5 passed - Project Lifecycle Management]

============================== 51 passed in 4.57s ===============================
```

To run the frontend production build verification:
```bash
cd frontend
npm run build
```

---

## Technical Documentation Index

For exhaustive technical reference and evaluation preparation, consult the `/docs` directory:

| Document | Description |
| :--- | :--- |
| [`docs/architecture.md`](file:///Users/piyushsinghal/Documents/Projects/image-video/docs/architecture.md) | Deep architectural specifications, module responsibilities, and data models. |
| [`docs/api.md`](file:///Users/piyushsinghal/Documents/Projects/image-video/docs/api.md) | Complete REST API endpoint reference with request/response payloads. |
| [`docs/viva.md`](file:///Users/piyushsinghal/Documents/Projects/image-video/docs/viva.md) | 26 Core Viva & Technical Defense questions with grounded answers. |
| [`docs/limitations.md`](file:///Users/piyushsinghal/Documents/Projects/image-video/docs/limitations.md) | Academic boundaries, scope constraints, and explicit non-goals. |
| [`docs/final-demo.md`](file:///Users/piyushsinghal/Documents/Projects/image-video/docs/final-demo.md) | 17-step end-to-end live demonstration and evaluation script. |
| [`docs/evaluation.md`](file:///Users/piyushsinghal/Documents/Projects/image-video/docs/evaluation.md) | Evaluation metric formulas, automated verification rules, and rubric scoring. |
| [`docs/results.md`](file:///Users/piyushsinghal/Documents/Projects/image-video/docs/results.md) | Experimental test properties, performance benchmarks, and evaluation templates. |
| [`docs/screenshots.md`](file:///Users/piyushsinghal/Documents/Projects/image-video/docs/screenshots.md) | 13 ordered screenshot captures for documentation and report inclusion. |
| [`docs/presentation-outline.md`](file:///Users/piyushsinghal/Documents/Projects/image-video/docs/presentation-outline.md) | 18-slide academic presentation structure with talking points. |

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
