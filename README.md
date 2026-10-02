# Generative Real Estate Walkthrough Pipeline

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI_0.115+-009688.svg?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Frontend-Next.js_16_(React_19)-000000.svg?style=flat-square&logo=next.js)](https://nextjs.org)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB.svg?style=flat-square&logo=python)](https://python.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0%2B-3178C6.svg?style=flat-square&logo=typescript)](https://www.typescriptlang.org)
[![Test Suite](https://img.shields.io/badge/Tests-51%20Passed-22c55e.svg?style=flat-square)]()

An end-to-end generative pipeline that transforms unordered real estate photographs into an architecturally ordered, cinematographic walkthrough video and interactive spatial inspection experience.

---

## Academic Scope & Scientific Boundaries

> **System Nature & Boundary Constraints:**
> - **Topological Rather Than Metric 3D:** The system builds a directed topological scene graph and camera motion plans to guide video diffusion models. It explicitly **does not** perform Structure-from-Motion (SfM), Visual SLAM, dense Neural Radiance Fields (NeRF), or 3D Gaussian Splatting (3DGS).
> - **Zero Spatial Hallucination:** If photographs for an intermediate hallway or staircase are missing from the input set, the system **never** synthesizes fictitious intermediate rooms. Adjacent scenes are stitched using restrained direct cuts or brief crossfades (0.4s).
> - **Immersive Projection Fidelity:** Standard perspective photographs are rendered using hardware-accelerated 2D bounded pan/zoom without artificial spherical distortion. Genuine 2:1 aspect ratio equirectangular images are mapped to an interactive 360° spherical projection with user override capabilities.

---

## System Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                      Next.js 16 Client Frontend                        │
│   (Studio Interface · 360° Spherical Viewer · Multi-Axis Evaluation)   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP / REST / Multipart
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                         FastAPI Backend Server                         │
│                                                                        │
│  ┌──────────────────────┐   ┌───────────────────────────────────────┐  │
│  │ Phase 1: Ingestion   │──▶│ Phase 2: Scene Understanding (VLM)    │  │
│  │ • Pillow Verification│   │ • Gemini 2.5 Flash Multimodal Vision  │  │
│  │ • SHA-256 Deduplication  │ • Room Classification & Lighting      │  │
│  │ • 2:1 Pano Detection │   │ • Manual Correction Overrides         │  │
│  └──────────────────────┘   └───────────────────┬───────────────────┘  │
│                                                 ▼                      │
│  ┌──────────────────────┐   ┌───────────────────────────────────────┐  │
│  │ Phase 4: Video Gen   │◀──│ Phase 3: Walkthrough Planning         │  │
│  │ • Gemini Veo 2.0 I2V │   │ • Topological Scene Graph             │  │
│  │ • Motion Safety Prompt   │ • Exterior ➔ Living ➔ Private Ordering│  │
│  │ • FFprobe Validation │   │ • Conservative Camera Motion Planner  │  │
│  └──────────┬───────────┘   └───────────────────────────────────────┘  │
│             ▼                                                          │
│  ┌──────────────────────┐   ┌───────────────────────────────────────┐  │
│  │ Phase 5: Assembly    │──▶│ Phase 6: Immersive Viewer & Audit     │  │
│  │ • FFmpeg Concat & Pad│   │ • 360° Equirectangular Projection     │  │
│  │ • Title Card Intro   │   │ • 6-Dimension Evaluation Framework    │  │
│  │ • Outdated Tracking  │   │ • Automated Verification & .txt Report│  │
│  └──────────────────────┘   └───────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Six-Phase Modular Pipeline

| Phase | Module | Primary Technical Responsibilities |
|---|---|---|
| **Phase 1** | **Foundation & Ingestion** | Multipart upload, byte-level Pillow validation (JPEG/PNG/WebP), size limits (<=20MB), min resolution (>=512x512), SHA-256 deduplication, EXIF orientation transpose, and isolated storage allocation. |
| **Phase 2** | **Scene Understanding** | Multimodal zero-shot scene inference with Gemini 2.5 Flash. Extracts room classification, lighting conditions, architectural features, visible doorways, and confidence scoring with user override support. |
| **Phase 3** | **Walkthrough Planning** | Directed scene graph generation, deterministic topological sorting (`Exterior` → `Foyer` → `Living` → `Kitchen` → `Bedrooms` → `Bathrooms` → `Outdoor`), camera trajectory assignment, and plan versioning. |
| **Phase 4** | **Image-to-Video Synthesis** | Scene-by-scene generative diffusion via Gemini Veo 2.0. Applies prompt grounding, negative safety prompts, retry queues, and automated FFprobe elementary stream validation. |
| **Phase 5** | **Video Assembly** | FFmpeg normalization (uniform H.264 / 24fps / 16:9), restrained transitions (straight cuts & 0.4s crossfades), intro title cards, HTML5 custom video player, and plan change invalidation tracking. |
| **Phase 6** | **Viewer & Evaluation** | Equirectangular 360° spherical canvas projection for panoramas, 2D pan/zoom for perspective photos, 6-dimension evaluation rubric, automated system checks, and exportable technical audit reports. |

---

## Evaluation & Quality Framework

The system incorporates a standardized 6-dimension quantitative scoring framework (1.0 to 5.0 scale) paired with automated non-subjective pipeline verification:

### 1. Evaluation Dimensions
1. **Visual Quality & Realism (≥ 4.0):** Photorealistic rendering fidelity, crisp architectural contours, and natural lighting.
2. **Property Consistency (≥ 4.0):** Layout, furniture, and materials faithful to source photographs.
3. **Scene Sequence & Flow (≥ 4.5):** Logical architectural progression through the property.
4. **Motion Naturalness (≥ 4.0):** Smooth, controlled camera movement without sudden jarring turns.
5. **Temporal Stability (≥ 3.5):** Minimal texture shimmer, object warping, or generative hallucinations.
6. **Walkthrough Usefulness (≥ 4.0):** Practical utility for real estate listing presentations and remote inspections.

### 2. Automated Pipeline Checks
- **Analysis Completeness:** Asserts 100% of uploaded images possess verified scene metadata.
- **Clip Availability:** Verifies individual MP4 video files exist for every scene in the sequence.
- **Stream Integrity:** Probes container headers and video elementary streams via FFprobe.
- **Plan Synchronization:** Computes SHA-256 plan fingerprint to detect out-of-date video assemblies.

---

## Project Structure

```
.
├── frontend/                     # Next.js 16 Web Application
│   ├── app/                      # App router & pages (/studio, landing)
│   ├── components/               # Specialized UI components (Viewer, Tracker, Editor)
│   ├── lib/                      # API client & image utilities
│   └── types/                    # TypeScript interfaces & Pydantic mirror types
│
├── backend/                      # Python FastAPI Application
│   ├── app/
│   │   ├── api/v1/projects.py    # REST routing for all pipeline stages
│   │   ├── core/                 # Config, custom exceptions & logging
│   │   ├── schemas/              # Pydantic validation schemas
│   │   └── services/             # Core business logic & AI orchestration
│   ├── storage/projects/<id>/    # Isolated per-project filesystem storage
│   └── tests/                    # 51 automated unit and integration tests
│
├── docs/                         # Detailed Technical Documentation
│   ├── architecture.md           # Deep subsystem architecture & data flow
│   ├── api.md                    # Complete REST API endpoint reference
│   ├── evaluation.md             # Metric definitions & automated verification criteria
│   ├── limitations.md            # Boundary constraints & academic non-goals
│   └── final-demo.md             # Step-by-step startup & demonstration walkthrough
│
├── .env.example                  # Environment configuration template
└── README.md
```

---

## Quick Start & Local Execution

### Prerequisites
- **Python**: `>= 3.10`
- **Node.js**: `>= 18.0` (Tested on Node v20 & v24)
- **FFmpeg**: Handled automatically via `imageio-ffmpeg` or system binary

### 1. Backend Setup
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
- **API URL:** `http://localhost:8000`
- **Interactive Documentation:** `http://localhost:8000/docs`
- **Health Check:** `http://localhost:8000/api/health`

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
- **Studio Interface:** `http://localhost:3000/studio`

---

## Automated Test Suite

The test suite validates every module across ingestion, scene inference, graph sorting, diffusion handling, FFmpeg assembly, and evaluation metrics:

```bash
cd backend
./venv/bin/pytest tests/ -v
```

```
============================== 51 passed in 3.99s ==============================
- Phase 1 (Foundation & Uploads): 14 passed
- Phase 2 (Scene Understanding): 7 passed
- Phase 3 (Walkthrough Planner): 10 passed
- Phase 4 (Image-to-Video Engine): 4 passed
- Phase 5 (Video Assembler): 6 passed
- Phase 6 (Evaluation & Reporting): 10 passed
```

---

## Detailed Documentation References

For exhaustive technical specifications, consult the `/docs` directory:
- [System Architecture & Data Flow](file:///Users/piyushsinghal/Documents/Projects/image-video/docs/architecture.md)
- [Complete REST API Reference](file:///Users/piyushsinghal/Documents/Projects/image-video/docs/api.md)
- [Evaluation Rubric & Quality Metrics](file:///Users/piyushsinghal/Documents/Projects/image-video/docs/evaluation.md)
- [Scope Boundaries & Non-Goals](file:///Users/piyushsinghal/Documents/Projects/image-video/docs/limitations.md)
- [End-to-End Demonstration Guide](file:///Users/piyushsinghal/Documents/Projects/image-video/docs/final-demo.md)
