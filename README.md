# Image-to-Video Walkthrough Generation for Real Estate Properties

**Academic Minor Project — Phases 1, 2 & 3: Foundation, Scene Understanding & Walkthrough Planner**

This project transforms a set of real estate property photographs into a coherent, cinematographic walkthrough video. The system processes interior and exterior photographs through a modular multi-stage pipeline: robust ingestion, vision-language scene understanding, scene graph construction, topological walkthrough path ordering, camera motion estimation, and transition planning.

> **Academic Prototype Scope Note:** Full physically accurate 3D reconstruction (e.g. SLAM, dense NeRF, 3D Gaussian Splatting) is explicitly out of scope. The system constructs a topological scene graph and camera motion plans to direct generative video diffusion models while strictly preserving the authentic architectural geometry and furniture of the original photographs.

---

## 1. Project Architecture

The application is structured as a decoupled frontend and backend:

```
image-to-video-walkthrough/
│
├── frontend/                     # Next.js 16 (React 19, TypeScript, Tailwind CSS)
│   ├── app/                      # App router (layout, globals.css, main page)
│   ├── components/               # UI components
│   │   ├── Dropzone.tsx          # Real estate photo upload area
│   │   ├── ImageGrid.tsx         # Uploaded images grid with badges
│   │   ├── SceneAnalysisModal.tsx# Scene understanding inspector & editor
│   │   ├── WalkthroughPlanView.tsx # Phase 3: Interactive walkthrough timeline
│   │   ├── PlannedSceneCard.tsx  # Phase 3: Scene card with camera & transition controls
│   │   ├── PhaseTracker.tsx      # Multi-phase progression status bar
│   │   └── ...
│   ├── lib/                      # API client, image helpers, utilities
│   ├── types/                    # TypeScript data models and API schemas
│   └── package.json
│
├── backend/                      # Python FastAPI application
│   ├── app/
│   │   ├── api/v1/               # Health, Project, Scene Analysis, and Plan REST endpoints
│   │   ├── core/                 # Config, error definitions, structured logging
│   │   ├── schemas/              # Pydantic models (Project, ImageMetadata, Scene, Plan)
│   │   ├── services/             # Core business services
│   │   │   ├── storage_service.py      # Filesystem persistence & path management
│   │   │   ├── project_service.py      # Project lifecycle & image uploads
│   │   │   ├── scene_analysis_service.py # Phase 2: Gemini multimodal visual analysis
│   │   │   └── walkthrough_planner/    # Phase 3: Walkthrough Planning Subsystem
│   │   │       ├── scene_graph_builder.py  # Scene graph nodes & connection edges
│   │   │       ├── ordering_engine.py      # Real estate walkthrough ordering
│   │   │       ├── camera_planner.py       # Camera motion & prompt generator
│   │   │       ├── transition_planner.py   # Inter-scene transition planning
│   │   │       └── planner_service.py      # GenerationPlan orchestration & versioning
│   │   └── main.py               # FastAPI entry point with CORS & exception handlers
│   ├── storage/                  # Local filesystem storage
│   │   └── projects/<id>/        # Isolated project folders with uploads/ & processed/
│   ├── tests/                    # 36 automated unit, integration, and planner tests
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
- **Pillow**: >= 10.2.0
- **Google GenAI SDK**: `google-genai` (Gemini 2.5 Flash for multimodal scene analysis)

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
VERSION=0.3.0
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

The backend includes 36 unit, integration, and algorithmic tests covering all Phase 1, Phase 2, and Phase 3 functionality:

```bash
cd backend
venv/bin/python -m pytest tests/ -v
```

### Test Coverage Highlights:
- **Phase 1: Foundation & Ingestion (19 tests)**
  - Health checks, project creation, non-empty validation, 404 handling.
  - Image validation: format checks (JPEG/PNG/WEBP), dimension thresholds (≥ 512×512), corrupted image rejection.
  - Size enforcement: 20 MB limit (HTTP 413).
  - Exact duplicate detection via SHA-256 file hashing (`DUPLICATE_IMAGE`).
  - Image deletion and physical disk cleanup from `uploads/` and `processed/`.
  - Asset streaming for original files and derived thumbnails.
- **Phase 2: Scene Understanding (7 tests)**
  - Schema serialization and validation for scene categories, lighting, view types, and features.
  - User correction persistence and manual override protection.
  - Multimodal Gemini prompt formatting and structured output parsing.
- **Phase 3: Walkthrough Planner & Camera Motion (10 tests)**
  - `SceneGraphBuilder`: Graph node construction and candidate relationship edges.
  - `OrderingEngine`: Real estate walkthrough sequence (Exterior → Entryway → Living Room → Dining → Kitchen → Bedrooms → Bathrooms → Balcony/Backyard).
  - `CameraPromptGenerator`: Room-specific camera motion selection and negative constraint preservation prompts.
  - `TransitionPlanner`: Visual match vs. straight cut transition determination based on scene connectivity.
  - `WalkthroughPlannerService`: Plan generation, version incrementing, user reordering, and rejection of invalid/duplicate scene IDs.
  - **Zero hallucinated rooms**: Strict invariant verified across all test scenarios.

---

## 6. API Reference

All API responses follow a standardized JSON envelope:

```json
{
  "success": true,
  "data": { ... },
  "error": null
}
```

### Phase 1: Projects & Ingestion
- `GET /api/health` — System status.
- `POST /api/projects` — Create property project with name.
- `GET /api/projects` — List all projects.
- `GET /api/projects/{id}` — Get project metadata and image list.
- `POST /api/projects/{id}/images` — Multi-image upload and validation.
- `GET /api/projects/{id}/images` — Retrieve validated images list.
- `DELETE /api/projects/{id}/images/{img_id}` — Delete image and clean disk.
- `GET /api/projects/{id}/images/{img_id}/file` — Serve original pristine image.
- `GET /api/projects/{id}/images/{img_id}/thumbnail` — Serve derived thumbnail.

### Phase 2: Scene Understanding
- `POST /api/projects/{id}/analyze` — Run real Gemini multimodal scene understanding.
- `PATCH /api/projects/{id}/images/{img_id}/scene` — Save user-corrected scene label and features.
- `GET /api/projects/{id}/images/{img_id}/analysis-file` — Serve normalized analysis image.

### Phase 3: Walkthrough Planner & Camera Motion
- `GET /api/projects/{id}/plan` — Retrieve current walkthrough plan (auto-generates baseline AI plan if none exists).
- `POST /api/projects/{id}/plan/rebuild` — Force re-generation of AI baseline walkthrough plan from latest scene graph.
- `PUT /api/projects/{id}/plan` — Save user-edited walkthrough plan (reordered shots, modified camera motions, custom prompts, scene exclusions). Increments `plan_version` and marks source as `user`.

---

## 7. Phase 4 Generation Contract

The output of Phase 3 is a validated `GenerationPlan` object ready for image-to-video generation:

```json
{
  "plan_id": "plan_project_123_v1",
  "project_id": "project_123",
  "plan_version": 1,
  "source": "ai",
  "total_estimated_duration_seconds": 16.0,
  "scenes": [
    {
      "order": 1,
      "scene_id": "scene_img_abc123",
      "image_id": "img_abc123",
      "scene_type": "living_room",
      "label": "Living Room",
      "reason": "Central living area positioned after entryway.",
      "camera": {
        "motion_type": "slow_forward",
        "prompt": "Smooth slow forward camera push through the living room, maintaining steady eye-level perspective...",
        "constraints": [
          "do not alter room geometry",
          "do not add furniture",
          "do not remove visible furniture",
          "avoid visual distortion"
        ],
        "duration_seconds": 4.0
      },
      "transition_to_next": {
        "type": "straight_cut",
        "duration_seconds": 0.5,
        "reason": "Sequential progression between connected zones"
      }
    }
  ]
}
```

---

## 8. Current Implementation Status

- [x] **Phase 1**: Ingestion, validation, deduplication, local storage, project management.
- [x] **Phase 2**: Real multimodal scene understanding via Gemini API, manual correction, visual metadata extraction.
- [x] **Phase 3**: Topological scene graph, deterministic walkthrough ordering, camera motion synthesis, transition planning, interactive glassmorphism UI, plan persistence and versioning.
- [ ] **Phase 4**: Image-to-Video Diffusion Generation & Multi-Clip Video Assembly.
