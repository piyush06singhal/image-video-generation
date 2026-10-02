# REST API Reference: Image-to-Video Walkthrough Generation

All endpoints are served from the FastAPI backend prefix `/api`. Responses adhere to standard `ApiResponse[T]` format:
```json
{
  "success": true,
  "data": { ... },
  "error": null,
  "timestamp": "2026-10-02T11:20:00Z"
}
```

---

## 1. System Health & Projects

### `GET /api/health`
Checks server and subsystem health.
- **Response:** `{"status": "healthy", "version": "0.6.0"}`

### `POST /api/projects`
Creates a new property session.
- **Body:** `{"name": "Luxury Ocean Villa"}`
- **Status:** `201 Created`

### `GET /api/projects`
Lists all existing project sessions.

### `GET /api/projects/{project_id}`
Retrieves project details, metadata, and uploaded images.

### `DELETE /api/projects/{project_id}?confirm=true`
Safely and irreversibly deletes project directory, uploads, plans, clips, final video, and evaluation data.
- **Query:** `confirm=true` (Required)

---

## 2. Image Ingestion & Assets (Phase 1)

### `POST /api/projects/{project_id}/images`
Uploads one or multiple property images. Performs Pillow format verification, size checks (<=20MB), dimension checks (>=512x512), SHA-256 deduplication, and derived thumbnail generation.
- **Form Data:** `files` (Multipart file list)
- **Status:** `201 Created`

### `GET /api/projects/{project_id}/images`
Lists all validated images in a project.

### `DELETE /api/projects/{project_id}/images/{image_id}`
Deletes an image and removes its files from disk.

### `GET /api/projects/{project_id}/images/{image_id}/file`
Streams the original pristine photograph.

### `GET /api/projects/{project_id}/images/{image_id}/thumbnail`
Streams the derived thumbnail.

---

## 3. Scene Understanding (Phase 2)

### `POST /api/projects/{project_id}/analyze`
Triggers Gemini multimodal vision analysis across project photographs.
- **Body (Optional):** `{"force_reanalyze": false, "image_ids": null}`

### `PATCH /api/projects/{project_id}/images/{image_id}/scene`
Manually updates or confirms scene type, features, or label.
- **Body:** `{"scene_type": "kitchen", "label": "Gourmet Kitchen", "user_confirmed": true}`

---

## 4. Walkthrough Planning (Phase 3)

### `GET /api/projects/{project_id}/plan`
Retrieves the current walkthrough generation plan (or generates baseline plan if none exists).

### `POST /api/projects/{project_id}/plan/rebuild`
Forces re-generation of the baseline plan from scene classifications.

### `PUT /api/projects/{project_id}/plan`
Saves custom user modifications (reordering, camera motion prompts, exclusions).

---

## 5. Image-to-Video Generation (Phase 4)

### `POST /api/projects/{project_id}/generate`
Triggers image-to-video clip generation for all scenes in the walkthrough plan.
- **Body (Optional):** `{"force_regenerate": false, "scene_ids": null}`

### `GET /api/projects/{project_id}/generation`
Retrieves overall clip generation progress and job status per scene.

### `POST /api/projects/{project_id}/scenes/{scene_id}/regenerate`
Forces regeneration of an individual scene video clip.

### `GET /api/projects/{project_id}/clips/{scene_id}/file`
Streams the generated MP4 clip for a scene.

### `GET /api/projects/{project_id}/clips/{scene_id}/download`
Downloads the generated scene clip as an MP4 attachment.

---

## 6. Video Assembly & Delivery (Phase 5)

### `POST /api/projects/{project_id}/assemble`
Normalizes clips, applies transitions, generates title card, and stitches the final walkthrough MP4.
- **Body (Optional):** `{"force_reassemble": false, "config": {"intro_title_enabled": true, "audio_enabled": false}}`

### `GET /api/projects/{project_id}/assembly`
Retrieves assembly job status.

### `GET /api/projects/{project_id}/final-video`
Retrieves metadata (duration, resolution, fps, codec, outdated status) for the final video.

### `GET /api/projects/{project_id}/final-video/file`
Streams the final assembled walkthrough MP4.

### `GET /api/projects/{project_id}/final-video/download`
Direct file download attachment for the final walkthrough MP4.

---

## 7. Panorama & Evaluation (Phase 6)

### `PATCH /api/projects/{project_id}/images/{image_id}/panorama`
Toggles or updates 360° equirectangular panorama classification.
- **Body:** `{"is_panoramic": true, "panoramic_type": "equirectangular"}`

### `POST /api/projects/{project_id}/evaluations`
Submits a 6-dimension human quality evaluation.
- **Body:**
  ```json
  {
    "visual_quality": 4,
    "property_consistency": 5,
    "scene_ordering": 5,
    "motion_quality": 4,
    "temporal_stability": 4,
    "walkthrough_usefulness": 5,
    "reviewer_name": "Lead Auditor",
    "comments": "Smooth camera trajectory and consistent lighting."
  }
  ```

### `GET /api/projects/{project_id}/evaluations`
Retrieves arithmetic evaluation averages and submission records.

### `POST /api/projects/{project_id}/scene-reviews`
Submits or updates per-scene review status and defect flags.
- **Body:**
  ```json
  {
    "scene_id": "scene_01",
    "status": "acceptable",
    "flags": [],
    "notes": "Crisp geometry."
  }
  ```

### `GET /api/projects/{project_id}/scene-reviews`
Retrieves list of per-scene quality reviews.

### `GET /api/projects/{project_id}/report`
Generates comprehensive JSON technical quality audit report with automated verification checks.

### `GET /api/projects/{project_id}/report/text`
Exports standardized plain-text audit report (`.txt`).
