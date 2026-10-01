# System Architecture: Image-to-Video Walkthrough Generation

## 1. Project Overview
The **Image-to-Video Walkthrough Generation** system transforms a set of unordered real estate photographs into a coherent, walkthrough-style property video. 

This project is an **academic minor-project implementation** structured across 6 clear phases:
1. **Phase 1 (Current)**: Image Ingestion, Validation, Metadata Extraction, and Local Storage Foundation.
2. **Phase 2**: Scene Understanding & Room Classification.
3. **Phase 3**: Walkthrough Image Ordering & Transition Graph Construction.
4. **Phase 4**: Image-to-Video Generation & Camera Motion Estimation.
5. **Phase 5**: Video Assembly, Inter-scene Crossfading, and Audio/Pacing.
6. **Phase 6**: Quantitative and Qualitative Evaluation.

> **Scope Note:** Full physically accurate 3D reconstruction (e.g. SLAM, dense NeRF, Gaussian Splatting) is explicitly out of scope for this prototype. The system operates via progressive 2D/2.5D visual continuity and generative interpolation.

---

## 2. Phase 1 Architecture

```
[ Next.js Frontend ] (Port 3000)
       │
       │ HTTP / JSON / FormData
       ▼
[ FastAPI Backend ] (Port 8000)
       │
       ├── Core / Config & Security (Path Traversal, Sanitization, Limits)
       ├── ImagePreprocessor (Pillow Integrity, Dimension & Format Check, Thumbnails)
       ├── Duplicate Detection (SHA-256 Checksum)
       └── StorageService (JSON State & Directory Segregation)
               │
               └── backend/storage/projects/<project_id>/
                       ├── project.json       (Session Metadata)
                       ├── uploads/           (Untouched Original Photographs)
                       └── processed/         (Derived Web Thumbnails & Normalized Previews)
```

---

## 3. Storage Hierarchy
Each real estate project is allocated an isolated directory identified by `project_YYYYMMDD_<hash>`:

```
backend/storage/projects/project_20261001_8a1f2c/
├── project.json
├── uploads/
│   ├── img_4b9a12_living_room.jpg
│   └── img_7c3e55_kitchen.jpg
└── processed/
    ├── thumb_img_4b9a12.jpg
    └── thumb_img_7c3e55.jpg
```

### Storage Invariants:
- **Original Source Preservation:** Files inside `uploads/` are stored untouched to serve as unmodified inputs for later AI processing.
- **Derived Separation:** Thumbnails and any normalized assets are stored in `processed/`.
- **Atomic State Storage:** `project.json` is updated atomically using temporary files and safe atomic rename operations.

---

## 4. API Endpoints (Phase 1)

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/health` | `GET` | Health check endpoint returning backend connectivity status. |
| `/api/projects` | `POST` | Create a new property project session. |
| `/api/projects` | `GET` | List all existing property projects. |
| `/api/projects/{project_id}` | `GET` | Retrieve project details, state, and image array. |
| `/api/projects/{project_id}/images` | `POST` | Upload and validate single or multiple property photographs. |
| `/api/projects/{project_id}/images` | `GET` | Retrieve list of validated image metadata for a project. |
| `/api/projects/{project_id}/images/{image_id}` | `DELETE` | Delete an image and remove all associated files from disk. |
| `/api/projects/{project_id}/images/{image_id}/file` | `GET` | Stream original image file. |
| `/api/projects/{project_id}/images/{image_id}/thumbnail` | `GET` | Stream derived thumbnail image. |

---

## 5. Image Validation & Duplicate Detection Rules
For each uploaded photograph:
1. **Size Limits:** File size must be between 1 byte and 20 MB (HTTP 413 on excess).
2. **Format Verification:** Validated using Pillow byte inspection (JPEG, PNG, WEBP allowed; HTTP 415 on unsupported format).
3. **Dimensions:** Minimum width and height of 512 × 512 pixels (HTTP 400 on undersized images).
4. **EXIF Orientation:** EXIF orientation tags are read and transposed so dimension reporting accurately matches visual orientation.
5. **Duplicate Detection:** SHA-256 hash is computed for file bytes. If the hash matches an existing image in the project, the upload is rejected with code `DUPLICATE_IMAGE` (HTTP 400).
6. **Path Traversal Prevention:** Client filenames are sanitized, and unique server-generated IDs (`img_xxxxxx`) prefix stored filenames.
