# Image-to-Video Walkthrough Generation for Real Estate Properties

**Academic Minor Project — Complete Pipeline: Phases 1 to 5 (Foundation, Scene Understanding, Route Planning, Clip Generation & Video Assembly)**

This project transforms a set of real estate property photographs into a coherent, cinematographic walkthrough video. The system processes interior and exterior photographs through a modular 5-stage pipeline: robust ingestion, vision-language scene understanding, scene graph construction, topological walkthrough path ordering, camera motion estimation, image-to-video clip synthesis, and FFmpeg video assembly with restrained transitions.

> **Academic Prototype Scope Note:** Full physically accurate 3D reconstruction (e.g. SLAM, dense NeRF, 3D Gaussian Splatting) is explicitly out of scope. The system constructs a topological scene graph and camera motion plans to direct generative video diffusion models while strictly preserving the authentic architectural geometry and furniture of the original photographs.
>
> **Spatial Honesty:** The final walkthrough is assembled from independently generated image-to-video clips. It does not constitute a physically reconstructed 3D tour, and does not hallucinate artificial intermediate hallway footage.

---

## 1. Project Architecture

The application is structured as a decoupled frontend and backend:

```
image-to-video-walkthrough/
│
├── frontend/                     # Next.js 16 (React 19, TypeScript, Tailwind CSS)
│   ├── app/                      # App router (layout, globals.css, main page, studio)
│   ├── components/               # UI components
│   │   ├── Dropzone.tsx          # Real estate photo upload area
│   │   ├── ImageGrid.tsx         # Uploaded images grid with badges
│   │   ├── SceneResultsView.tsx  # Phase 2: Scene understanding inspector & editor
│   │   ├── WalkthroughPlanView.tsx # Phase 3: Interactive walkthrough timeline
│   │   ├── GenerationView.tsx    # Phase 4: Image-to-video clip generation studio
│   │   ├── FinalWalkthroughView.tsx # Phase 5: Final video player & download
│   │   ├── StudioPhaseTracker.tsx# 5-Phase studio tracker bar
│   │   └── ...
│   ├── lib/                      # API client, image helpers, utilities
│   ├── types/                    # TypeScript data models and API schemas
│   └── package.json
│
├── backend/                      # Python FastAPI application
│   ├── app/
│   │   ├── api/v1/               # Health, Project, Scene, Plan, Video & Assembly REST endpoints
│   │   ├── core/                 # Config, error definitions, structured logging
│   │   ├── schemas/              # Pydantic models (Project, Scene, Plan, Generation, Assembly)
│   │   ├── services/             # Core business services
│   │   │   ├── storage_service.py      # Filesystem persistence & path management
│   │   │   ├── project_service.py      # Project lifecycle & image uploads
│   │   │   ├── scene_analysis_service.py # Phase 2: Gemini multimodal visual analysis
│   │   │   ├── walkthrough_planner/    # Phase 3: Walkthrough Planning Subsystem
│   │   │   ├── video_generation/       # Phase 4: Image-to-Video Diffusion Engine
│   │   │   └── video_assembler/        # Phase 5: Video Assembly & Transitions
│   │   │       ├── ffmpeg_engine.py    # FFmpeg probe, normalization, concat, and intro cards
│   │   │       └── service.py          # VideoAssemblerService orchestration & metadata
│   │   └── main.py               # FastAPI entry point with CORS & exception handlers
│   ├── storage/                  # Local filesystem storage
│   │   └── projects/<id>/        # Isolated project folders (uploads, analysis, plans, clips, final)
│   ├── tests/                    # 46 automated unit, integration, and assembly tests
│   └── requirements.txt
│
├── docs/                         # Architectural diagrams and technical specifications
├── .env.example                  # Environment configuration template
└── README.md
```

---

## 2. Requirements

- **Node.js**: >= 18.0 (Tested on Node v24)
- **npm**: >= 9.0
- **Python**: >= 3.10 (Tested on Python 3.14)
- **FastAPI / Uvicorn**
- **FFmpeg**: Bundled via `imageio-ffmpeg`
- **Pillow**: >= 10.2.0
- **Google GenAI SDK**: `google-genai` (Gemini 2.5 Flash for scene analysis & Gemini Veo 2.0 for video generation)

---

## 3. Environment Variables

Configure `.env` files based on `.env.example`:

### Frontend (`frontend/.env.local`)
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Backend (`backend/.env`)
```env
PROJECT_NAME="Image-to-Video Walkthrough Generation"
VERSION=0.5.0
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

## 4. How to Run Locally

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

## 5. Running Automated Backend Tests

The backend includes 46 unit, integration, and algorithmic tests covering all Phases 1 through 5:

```bash
cd backend
venv/bin/python -m pytest tests/ -v
```

### Test Coverage Highlights:
- **Phase 1: Foundation & Ingestion (14 tests)**: Health checks, project creation, validation, deduplication, thumbnail generation.
- **Phase 2: Scene Understanding (7 tests)**: Multimodal scene classification, lighting analysis, feature extraction, manual override.
- **Phase 3: Walkthrough Planner & Camera Motion (10 tests)**: Scene graph construction, architectural order sorting, negative safety prompts, plan lifecycle.
- **Phase 4: Image-to-Video Generation (4 tests)**: Clip validator, generation state transitions, retry queue, clip streaming endpoints.
- **Phase 5: Video Assembly & Transitions (6 tests)**: FFmpeg probe, normalization, title card generation, missing clip halt, end-to-end concat assembly, outdated plan detection, and video download endpoints.

---

## 6. Phase 5: Video Assembly Subsystem

The **Video Assembler** transforms individual generated scene video clips into a single property walkthrough MP4:

1. **Source of Truth Ordering**: Strictly adheres to `GenerationPlan.scenes[].order` without reordering or hallucinating rooms.
2. **Pre-flight Clip Validation**: Probes each approved scene clip using FFprobe. Missing or corrupted clips halt assembly with descriptive diagnostics (e.g. *"Walkthrough cannot be assembled because the Kitchen clip is unavailable."*).
3. **Normalization Engine**: Re-encodes clips to uniform resolution (720p/1080p), framerate (24fps), and H.264 video codec with letterbox padding to preserve authentic property geometry without distortion.
4. **Cinematic Transitions**: Supports clean direct cuts (`straight_cut`) and restrained crossfades (`short_crossfade`, 0.25–0.5s). No flashy wipes, spin transitions, or artificial hallway morphing.
5. **Title Intro Card**: Optional 1.5-second dark-luxury title card displaying property name and subtitle.
6. **Outdated Video Tracking**: Computes SHA-256 fingerprint of the generation plan. If the plan is modified after assembly, the final video is marked as `is_outdated` with immediate re-assembly available.
7. **Storage & Delivery**: Persists output to `projects/<project_id>/final/walkthrough.mp4` with verified `metadata.json` and direct streaming/download endpoints.

---

## 7. Current Implementation Status

- [x] **Phase 1**: Ingestion, validation, deduplication, local storage, project management.
- [x] **Phase 2**: Real multimodal scene understanding via Gemini API, manual correction, visual metadata extraction.
- [x] **Phase 3**: Topological scene graph, deterministic walkthrough ordering, camera motion synthesis, transition planning, interactive glassmorphism UI, plan persistence and versioning.
- [x] **Phase 4**: Real Image-to-Video Diffusion Generation (Gemini Veo 2.0), retry queue, clip validation, video playback preview.
- [x] **Phase 5**: Video Assembly, FFmpeg normalization, restrained transitions, intro title cards, HTML5 video player, MP4 download, outdated plan detection, and automated test suite.
