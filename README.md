# Image-to-Video Walkthrough Generation for Real Estate Properties

**Academic Minor Project — Complete Pipeline: Phases 1 to 6 (Foundation, Scene Understanding, Route Planning, Clip Generation, Video Assembly & Immersive Evaluation)**

This system transforms a set of real estate photographs into a coherent, cinematographic walkthrough video and interactive property inspection experience. The architecture is modular and deterministic: robust photo ingestion, vision-language scene understanding (Gemini 2.5 Flash), topological scene graph construction, architectural walkthrough path ordering, camera motion estimation, image-to-video clip synthesis (Gemini Veo 2.0), FFmpeg video assembly with restrained transitions, and an immersive 360° / high-res inspection viewer accompanied by a multi-dimensional prototype quality evaluation framework.

> **Academic Prototype Scope Note:** Full physically accurate 3D reconstruction (e.g. SLAM, dense NeRF, 3D Gaussian Splatting) is explicitly out of scope. The system constructs a topological scene graph and camera motion plans to direct generative video diffusion models while strictly preserving the authentic architectural geometry and furniture of the original photographs.
>
> **Spatial Honesty & Scope Limitation:** The walkthrough is assembled from independently generated image-to-video clips and photograph projections. It does not constitute a physically reconstructed 3D tour, and does not hallucinate artificial intermediate hallway footage. The immersive inspector provides equirectangular spherical viewing for genuine 360° panoramas and high-resolution 2D pan/zoom for standard perspective photographs.

---

## 1. Project Architecture

The application is structured as a decoupled frontend (Next.js 16 + Tailwind CSS) and backend (Python FastAPI):

```
image-to-video-walkthrough/
│
├── frontend/                     # Next.js 16 (React 19, TypeScript, Vanilla CSS + Tailwind)
│   ├── app/                      # App router (layout, globals.css, main page, studio)
│   ├── components/               # UI components
│   │   ├── Dropzone.tsx          # Real estate photo upload area
│   │   ├── ImageGrid.tsx         # Uploaded images grid with badges
│   │   ├── SceneResultsView.tsx  # Phase 2: Scene understanding inspector & editor
│   │   ├── WalkthroughPlanView.tsx # Phase 3: Interactive walkthrough timeline
│   │   ├── GenerationView.tsx    # Phase 4: Image-to-video clip generation studio
│   │   ├── FinalWalkthroughView.tsx # Phase 5 & 6: Final video player & mode switcher
│   │   ├── ImmersiveSceneViewer.tsx # Phase 6: 360° spherical canvas & high-res inspector
│   │   ├── EvaluationSection.tsx # Phase 6: 6-dimension evaluation & scoring form
│   │   ├── TechnicalReportModal.tsx # Phase 6: Automated checks & technical report modal
│   │   ├── StudioPhaseTracker.tsx# Multi-phase studio tracker bar
│   │   └── ...
│   ├── lib/                      # API client, image helpers, utilities
│   ├── types/                    # TypeScript data models and API schemas
│   └── package.json
│
├── backend/                      # Python FastAPI application
│   ├── app/
│   │   ├── api/v1/               # Health, Project, Scene, Plan, Video, Assembly & Evaluation endpoints
│   │   ├── core/                 # Config, error definitions, structured logging
│   │   ├── schemas/              # Pydantic models (Project, Scene, Plan, Generation, Assembly, Evaluation)
│   │   ├── services/             # Core business services
│   │   │   ├── storage_service.py      # Filesystem persistence & path management
│   │   │   ├── project_service.py      # Project lifecycle, uploads & safe deletion
│   │   │   ├── scene_analysis_service.py # Phase 2: Gemini multimodal visual analysis
│   │   │   ├── image_preprocessor.py   # Phase 6: Equirectangular 2:1 panorama detection
│   │   │   ├── walkthrough_planner/    # Phase 3: Walkthrough Planning Subsystem
│   │   │   ├── video_generation/       # Phase 4: Image-to-Video Diffusion Engine
│   │   │   ├── video_assembler/        # Phase 5: Video Assembly & Transitions
│   │   │   └── evaluation_service.py   # Phase 6: Evaluation metrics & Technical Report generator
│   │   └── main.py               # FastAPI entry point with CORS & exception handlers
│   ├── storage/                  # Local filesystem storage
│   │   └── projects/<id>/        # Isolated project folders (uploads, analysis, plans, clips, final, eval)
│   ├── tests/                    # 51 automated unit, integration, and evaluation tests
│   └── requirements.txt
│
├── docs/                         # Architectural diagrams and technical specifications
├── .env.example                  # Environment configuration template
└── README.md
```

---

## 2. Six-Phase Modular Pipeline

| Phase | Module | Key Capabilities |
|---|---|---|
| **Phase 1** | Foundation & Ingestion | Real photo upload, format validation (JPEG/PNG/WebP), aspect ratio preservation, perceptual deduplication, and fast thumbnail generation. |
| **Phase 2** | Scene Understanding | Vision-language inference via Gemini 2.5 Flash, classification (exterior, living room, kitchen, bedroom, etc.), lighting conditions, architectural features, and manual correction overrides. |
| **Phase 3** | Walkthrough Planning | Directed scene graph generation, topological ordering (Exterior → Entrance → Social → Private → Outdoor), camera motion trajectories, restrained transition selection, and plan versioning. |
| **Phase 4** | Image-to-Video Generation | Per-scene diffusion synthesis via Gemini Veo 2.0 with prompt grounding, camera constraints, negative prompt filtering, retry queues, and FFprobe validation. |
| **Phase 5** | Video Assembly | FFmpeg normalization (uniform H.264, 24fps), restrained transitions (straight cuts & 0.4s crossfades), intro title cards, HTML5 video player, MP4 download, and plan staleness detection. |
| **Phase 6** | Immersive Viewer & Evaluation | 360° spherical canvas projection for 2:1 panoramas, high-res pan/zoom for standard photos, scene reviews, 6-dimension evaluation framework, automated system verification checks, and technical text report export. |

---

## 3. Phase 6: Immersive Viewer & Quality Evaluation

### Part A — Immersive Property Viewer
- **Dual Mode Experience**: Switch instantly between `[ 🎬 Cinematic Walkthrough ]` (assembled video player) and `[ 🌐 Immersive Scene Viewer ]` (scene-by-scene spatial inspector).
- **True Equirectangular 360° Projection**:
  - Automatically identifies 2:1 aspect ratio images as equirectangular spherical panoramas during upload.
  - Interactive Canvas renderer supporting yaw/pitch dragging, field-of-view (FOV) zooming, continuous auto-turn, wrap-around seam handling, and reset to origin.
  - Manual override toggle allowing users to switch between 360° spherical mode and standard 2D photo mode.
- **High-Resolution 2D Pan/Zoom**:
  - Standard perspective photos are rendered with hardware-accelerated 2D transforms and bounded pan/zoom (1.0x to 4.0x) without distortion or false spherical warping.
- **Scene-by-Scene Navigation & Media Comparison**:
  - Stepper bar and thumbnail navigation across all planned scenes.
  - Quick toggle between the original **Source Photograph** and the **Generated Video Clip**.
- **Per-Scene Quality Review Flags**:
  - Reviewers can tag each room as `Acceptable`, `Needs Review`, or `Failed`.
  - Specific defect checkboxes: Geometry Distortion, Object Inconsistency, Flickering/Shimmer, Unnatural Motion Velocity, Lighting Drift.

### Part B — Evaluation & Technical Quality Reporting
- **6-Dimension Evaluation Framework** (1 to 5 scale):
  1. **Visual Quality & Realism**: Photorealistic rendering fidelity, crisp architectural details, lighting naturalness.
  2. **Property Consistency**: Preservation of layout, furniture, materials, and structures from source photos.
  3. **Scene Sequence & Flow**: Logical architectural path from exterior/entry to living areas and private rooms.
  4. **Motion Naturalness**: Smooth, controlled camera trajectories without disorienting sudden turns.
  5. **Temporal Stability**: Absence of morphing, flickering textures, warping objects, or structural hallucinations.
  6. **Walkthrough Usefulness**: Practical value as a realistic real estate sales, listing, or buyer inspection tool.
- **Automated Verification Checks**:
  - Verification that all scenes are analyzed, all clips are generated, the final video is assembled, video stream integrity is validated, and plan synchronization is intact.
- **Technical Report Generation**:
  - Downloadable standardized `.txt` audit report containing property metadata, system specifications, automated verification checks, arithmetic evaluation averages, and per-scene review summaries.
- **Safe Project Cleanup**:
  - Project deletion endpoint requiring explicit confirmation (`?confirm=true`) to safely clean up all project media and metadata.

---

## 4. Environment Variables

Configure `.env` files based on `.env.example`:

### Frontend (`frontend/.env.local`)
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Backend (`backend/.env`)
```env
PROJECT_NAME="Image-to-Video Walkthrough Generation"
VERSION=0.6.0
API_PREFIX=/api
STORAGE_DIR=storage
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
MAX_IMAGE_SIZE_BYTES=20971520
MIN_IMAGE_WIDTH=512
MIN_IMAGE_HEIGHT=512
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
```

---

## 5. How to Run Locally

### Running the Backend
1. Open a terminal in `backend/`:
   ```bash
   cd backend
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
2. Start the FastAPI development server:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
3. Backend is live at `http://localhost:8000`:
   - Interactive Swagger API Docs: `http://localhost:8000/docs`
   - Health Check: `http://localhost:8000/api/health`

### Running the Frontend
1. Open a terminal in `frontend/`:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
2. Access the web application at `http://localhost:3000`.

---

## 6. Running Automated Backend Tests

The backend test suite includes **51 comprehensive unit and integration tests** covering all 6 phases:

```bash
cd backend
./venv/bin/pytest tests/ -v
```

### Test Suite Breakdown:
- **Phase 1: Foundation & Ingestion (14 tests)**: Health checks, project lifecycle, validation, deduplication, thumbnail generation.
- **Phase 2: Scene Understanding (7 tests)**: Multimodal scene classification, lighting analysis, feature extraction, manual override.
- **Phase 3: Walkthrough Planner & Camera Motion (10 tests)**: Scene graph construction, architectural order sorting, negative safety prompts, plan lifecycle.
- **Phase 4: Image-to-Video Generation (4 tests)**: Clip validator, generation state transitions, retry queue, clip streaming endpoints.
- **Phase 5: Video Assembly & Transitions (6 tests)**: FFmpeg probe, normalization, title card generation, missing clip halt, end-to-end concat assembly, outdated plan detection, and video download endpoints.
- **Phase 6: Evaluation & Reporting (10 tests)**: Panorama detection, panorama metadata overrides, 6-dimension evaluation scoring arithmetic, scene review flags, automated integrity checks, technical text report generation, and safe project cleanup.

---

## 7. Current Implementation Status

- [x] **Phase 1**: Ingestion, validation, deduplication, local storage, project management.
- [x] **Phase 2**: Real multimodal scene understanding via Gemini API, manual correction, visual metadata extraction.
- [x] **Phase 3**: Topological scene graph, deterministic walkthrough ordering, camera motion synthesis, transition planning, interactive glassmorphism UI, plan persistence and versioning.
- [x] **Phase 4**: Real Image-to-Video Diffusion Generation (Gemini Veo 2.0), retry queue, clip validation, video playback preview.
- [x] **Phase 5**: Video Assembly, FFmpeg normalization, restrained transitions, intro title cards, HTML5 video player, MP4 download, outdated plan detection.
- [x] **Phase 6**: Immersive Scene Viewer (360° spherical projection for panoramas + high-res 2D pan/zoom), per-scene quality reviews, 6-dimension human evaluation framework, automated integrity checks, exportable technical audit report, and safe project deletion.
