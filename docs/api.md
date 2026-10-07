# REST API Reference: Image-to-Video Walkthrough Generation

All endpoints are served from the FastAPI backend prefix `/api`. Responses adhere to standard `ApiResponse[T]` format:
```json
{
  "success": true,
  "data": { ... },
  "error": null,
  "timestamp": "<server-generated ISO-8601 timestamp>"
}
```

---

## 1. System Health & Projects

### `GET /api/health`
Checks server and subsystem health.
- **Response data:** `{"status": "healthy", "service": "walkthrough-backend"}`

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

## Cinematic Render Options (cross-cutting: Phases 4–5)

One creative configuration per project drives both Phase 4 and Phase 5. It is persisted
as `render_options.json` inside the project directory, so a later regenerate/reassemble
reproduces the same look without re-sending the form.

### `GET /api/projects/render-options/presets`
Lists the built-in style presets (`cinematic_luxury`, `modern_minimal`, `energetic_reel`,
`documentary_tour`, `quick_draft`) with human descriptions and their option values.

### `GET /api/projects/{project_id}/render-options`
Returns the project's effective options (persisted values, else the house style).

### `PATCH /api/projects/{project_id}/render-options`
Applies a preset and/or partial overrides.
- **Body:** `{"preset": "energetic_reel", "options": {"music_volume": 0.4}, "replace": false}`
- `preset` re-bases the whole option set; `options` merges onto what is already saved.

Option fields: `scene_duration_seconds`, `motion_intensity`, `camera_variety`,
`depth_parallax`, `motion_blur`, `transition_style`, `transition_duration_seconds`,
`aspect_ratio` (`16:9`/`9:16`/`1:1`), `resolution` (`720p`/`1080p`/`1440p`), `fps`,
`intro_title_enabled`/`intro_title_text`/`intro_duration_seconds`,
`outro_enabled`/`outro_text`/`outro_duration_seconds`, `room_labels_enabled`,
`room_counter`, `brand_text`, `color_grade`, `vignette`, `film_grain`,
`cinematic_bloom`, `letterbox`, `music_enabled`, `music_style`, `music_volume`.

Production-value fields in one line each:
- `depth_parallax` — estimates per-pixel depth locally and moves near pixels further
  than far ones, so a camera move over a still has real dimensionality. Falls back to
  a flat camera move when the depth model is absent.
- `motion_blur` — trailing-shutter blur on fast movement.
- `cinematic_bloom` — highlight halation: only pixels above the gate glow, smeared
  wide horizontally the way a fast lens bleeds light.
- `letterbox` — scope bars, landscape output only. **Off by default**, because bars
  remove 11% of the picture the client is paying to see.
- `room_counter` — adds “03 / 08” and a tour progress line to each lower-third.
- `brand_text` — a discreet agency mark under the title and end cards.

`transition_style` accepts `straight_cut`, `crossfade`, `fade_to_black`,
`slide_left`, `wipe_up`, `blur_dissolve` and `smooth_left`. The last two are
motion-bridged cuts: they smear the outgoing frame as the incoming one arrives, so
the eye reads one continuous move instead of two photographs swapping places.

`color_grade` accepts `none`, `warm_luxury`, `golden_hour`, `cool_modern`,
`cinematic_teal` and `noir`. Every grade lifts shadows off true black and rolls the
highlights off below clipping rather than blanket-darkening the frame.

Sound design is not an option — every score carries a whoosh on each cut, a riser
into the first shot and a button on the end card, placed from the assembly's own cut
positions.

Changing an option that reshapes the clips (`scene_duration_seconds`, `aspect_ratio`,
`resolution`, `fps`, `motion_intensity`, `camera_variety`, `depth_parallax`,
`motion_blur`) makes already-generated clips stale; `GET /generation` reports `clips_outdated`, and the next `POST /generate`
regenerates them. Any change marks the assembled video outdated via
`render_options_hash` — and *reverting* to the settings a cut was built with makes it
valid again, so no needless re-render is triggered.

---

## 5. Image-to-Video Generation (Phase 4)

### `POST /api/projects/{project_id}/generate`
Triggers image-to-video clip generation for all scenes in the walkthrough plan.
Clips are reused only when they were rendered with the project's *current* options.
- **Body (Optional):** `{"force_regenerate": false, "scene_ids": null, "render_options": null}`

### `GET /api/projects/{project_id}/generation`
Retrieves overall clip generation progress and job status per scene.

### `POST /api/projects/{project_id}/scenes/{scene_id}/regenerate`
Forces regeneration of an individual scene video clip.

### `POST /api/projects/{project_id}/generation/jobs/{job_id}/retry`
Retries one failed or paused scene job, subject to the configured retry limit.

### `GET /api/projects/{project_id}/clips/{scene_id}/file`
Streams the generated MP4 clip for a scene.

### `GET /api/projects/{project_id}/clips/{scene_id}/download`
Downloads the generated scene clip as an MP4 attachment.

### `POST /api/projects/{project_id}/local-slideshow`
Creates a deterministic local image slideshow walkthrough without calling Gemini/Veo.
- **Response:** `FinalVideoMetadata`
- **Use:** Free-tier quota fallback or offline demonstration mode.

---

## 6. Video Assembly & Delivery (Phase 5)

### `POST /api/projects/{project_id}/assemble`
Conforms every clip to the target frame, burns optional room labels, builds intro/outro
cards over blurred plates of the property's own photography, applies the chosen
transitions and colour grade (with vignette/grain), synthesises a royalty-free score,
and writes the final walkthrough MP4.
- **Body (Optional):** `{"force_reassemble": false, "render_options": null, "config": null}`
- `render_options` (optional) is saved for the project before assembling.
- `config` is a legacy override path. Only fields you explicitly set are applied, so an
  empty config means "use the project's render options".

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
