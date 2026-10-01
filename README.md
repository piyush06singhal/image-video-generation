# Image-to-Video Walkthrough Generation for Real Estate Properties

**Academic Minor Project — Phase 1: Foundation, Image Ingestion & Validation**

This project transforms a set of real estate property photographs into a coherent walkthrough-style video. The system processes interior and exterior photographs through a multi-stage pipeline comprising scene understanding, topological ordering, image-to-video diffusion, and multi-clip video assembly.

> **Academic Prototype Scope Note:** Full physically accurate 3D reconstruction (e.g. SLAM, dense NeRF, Gaussian Splatting) is explicitly out of scope. In later phases, the system generates visual transitions using generative interpolation and camera motion estimation while strictly preserving the integrity of original source photographs.

---

## 1. Project Architecture

The application is structured with a decoupled frontend and backend:

```
image-to-video-walkthrough/
│
├── frontend/                     # Next.js 16 (React 19, TypeScript, Tailwind CSS)
│   ├── app/                      # App router (layout, globals.css, main page)
│   ├── components/               # UI components (Dropzone, ImageGrid, Header, Modals)
│   ├── lib/                      # API client, image helpers, utilities
│   ├── types/                    # TypeScript data models and API schemas
│   └── package.json
│
├── backend/                      # Python FastAPI application
│   ├── app/
│   │   ├── api/v1/               # Health and Project REST endpoints
│   │   ├── core/                 # Config, error definitions, structured logging
│   │   ├── schemas/              # Pydantic models (Project, ImageMetadata, ApiResponse)
│   │   ├── services/             # StorageService, ProjectService, ImagePreprocessor
│   │   ├── utils/                # File sanitization, hashing, ID generators
│   │   └── main.py               # FastAPI entry point with CORS & exception handlers
│   ├── storage/                  # Local filesystem storage
│   │   └── projects/<id>/        # Isolated project folders with uploads/ & processed/
│   ├── tests/                    # Comprehensive pytest test suite (19 unit/integration tests)
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

---

## 3. Environment Variables

Create `.env` or `.env.local` files based on `.env.example`:

### Frontend (`frontend/.env.local`)
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Backend (`backend/.env`)
```env
PROJECT_NAME="Image-to-Video Walkthrough Generation"
VERSION=0.1.0
API_PREFIX=/api
STORAGE_DIR=storage
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
MAX_IMAGE_SIZE_BYTES=20971520
MIN_IMAGE_WIDTH=512
MIN_IMAGE_HEIGHT=512
```

---

## 4. How to Run Locally

### Option A: Running Backend
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
3. Backend will be live at `http://localhost:8000`.
   - API Docs: `http://localhost:8000/docs`
   - Health Check: `http://localhost:8000/api/health`

### Option B: Running Frontend
1. Open a terminal in `frontend/`:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
2. Access the web interface at `http://localhost:3000`.

---

## 5. Running Automated Backend Tests

The backend includes a comprehensive pytest suite covering all core functional requirements:

```bash
cd backend
PYTHONPATH=. venv/bin/pytest -v
```

### Test Coverage Highlights:
- **Health Check**: Validates `/api/health` connectivity and envelope structure.
- **Project Lifecycle**: Tests project creation, validation of non-empty names, listing, and 404 handling.
- **Image Validation**: Verifies format restrictions (JPEG/PNG/WEBP), dimension thresholds (min 512×512), and corruption checks.
- **Size Enforcement**: Tests 20 MB size limit (HTTP 413).
- **Duplicate Detection**: Tests exact SHA-256 duplicate detection with `DUPLICATE_IMAGE` error response.
- **Image Deletion & Disk Cleanup**: Verifies physical deletion from `uploads/` and `processed/` folders.
- **Asset Serving**: Tests streaming of original files and derived thumbnails.

---

## 6. API Reference (Phase 1)

All API responses follow a standardized JSON envelope:

**Success Response Format:**
```json
{
  "success": true,
  "data": { ... },
  "error": null
}
```

**Error Response Format:**
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error description",
    "details": null
  }
}
```

### Endpoints:
- `GET /api/health` — System status.
- `POST /api/projects` — Create property project with name.
- `GET /api/projects` — List all projects.
- `GET /api/projects/{project_id}` — Get project metadata and image list.
- `POST /api/projects/{project_id}/images` — Multi-image upload and validation.
- `GET /api/projects/{project_id}/images` — Retrieve validated images list.
- `DELETE /api/projects/{project_id}/images/{image_id}` — Delete image.
- `GET /api/projects/{project_id}/images/{image_id}/file` — Download original image.
- `GET /api/projects/{project_id}/images/{image_id}/thumbnail` — Download derived thumbnail.

---

## 7. Current Implementation Status (Phase 1)

- [x] Next.js 16 + TypeScript + Tailwind CSS real estate user interface.
- [x] Python FastAPI backend with modular service architecture.
- [x] Real multipart multi-image upload directly to filesystem storage.
- [x] Segregated storage (`uploads/` for pristine originals, `processed/` for derived thumbnails).
- [x] Robust image validation (Pillow format verification, size limits, minimum dimensions).
- [x] Image metadata extraction (dimensions, format, file size, aspect ratio, SHA-256).
- [x] Exact duplicate detection via SHA-256 file hashing.
- [x] Atomic JSON project persistence (`project.json`).
- [x] Error handling with structured API envelopes and HTTP status codes.
- [x] 19 automated pytest unit and integration tests.

---

## 8. Next Step (Phase 2 Roadmap)

The next step is **Phase 2: Scene Understanding & Room Classification**:
1. Implement vision-language scene classification (e.g. CLIP / ViT / Gemini API) to classify images into standard room categories (*Living Room, Kitchen, Bedroom, Balcony, Bathroom, Exterior*).
2. Extract architectural features and spatial relationship cues for subsequent path ordering.
