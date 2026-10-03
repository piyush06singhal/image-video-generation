# System Architecture: Image-to-Video Walkthrough Generation

## 1. Executive Summary & Pipeline Flow

The **Image-to-Video Walkthrough Generation System** converts unordered real estate photographs into a coherent, cinematographic walkthrough video and spatial inspection interface. The system avoids false claims of full 3D reconstruction/SLAM and instead uses deterministic topological scene graphs, conservative camera motion trajectories, AI video diffusion models, and FFmpeg normalization.

```
[ Frontend: Next.js 16 + Tailwind CSS ] (Port 3000)
       │
       │ HTTP / JSON / FormData
       ▼
[ Backend: FastAPI Server ] (Port 8000)
       │
       ├── Project Manager & Storage Service (Isolated filesystem persistence)
       │
       ├── 1. Image Ingestion & Preprocessor
       │      └── Validation (Pillow), EXIF transpose, deduplication (SHA-256), 2:1 panorama detection
       │
       ├── 2. Scene Understanding Subsystem (VLM)
       │      └── Multimodal visual analysis (Gemini 2.5 Flash), room classification, lighting, features
       │
       ├── 3. Walkthrough Planner Subsystem
       │      ├── Scene Graph Builder (Spatial connection heuristics)
       │      └── Topological Ordering Engine (Exterior → Entrance → Social → Private → Outdoor)
       │
       ├── 4. Camera Motion & Transition Planner
       │      └── Conservative motion trajectories, duration & direct preservation constraints
       │
       ├── 5. Image-to-Video Diffusion Engine
       │      ├── Single-flight submission pacing, bounded backoff, and quota-aware pause state
       │      ├── Persisted generation metadata with startup recovery for queued jobs
       │      └── Scene-by-scene video generation (Gemini Veo 3.1) & validation
       │
       ├── 6. FFmpeg Video Assembler Engine
       │      └── Normalization (uniform H.264 / 24fps), intro title cards, concatenation & crossfades
       │
       ├── 7. Immersive Scene Viewer
       │      └── 360° Equirectangular Canvas projection & High-Resolution 2D pan/zoom
       │
       ├── 8. Human Evaluation & Quality Reporting
       │      └── 6-dimension evaluation rubric, automated checks, and technical text report generator
       │
       └── 9. Local Fallback Delivery
              └── Aspect-ratio-preserving image slideshow when remote quota is unavailable
```

---

## 2. Core Subsystems & Responsibilities

### 2.1 Vision-Language Model (VLM - Gemini 2.5 Flash)
- **Role:** Extracts semantic and physical room characteristics from uploaded photographs.
- **Outputs:** `scene_type`, `description`, `features`, `lighting`, `visible_connections`, `camera_characteristics`, and `confidence` score.
- **Constraints:** Never hallucinates unseen rooms (e.g. seeing a doorway does not invent a bedroom behind it).

### 2.2 Walkthrough Planner & Scene Graph
- **Role:** Constructs a directed scene graph representing property navigation topology.
- **Sorting Logic:** Applies architectural hierarchy:
  1. `exterior_front`
  2. `entrance_foyer`
  3. `living_room` / `dining_room` / `open_plan`
  4. `kitchen`
  5. `hallway_corridor` / `stairs`
  6. `master_bedroom` / `bedroom`
  7. `bathroom`
  8. `balcony_terrace` / `backyard_garden`
- **Plan Lifecyle:** Supports user reordering, exclusions, manual classifications, and plan versioning.

### 2.3 Camera Motion Planner
- **Role:** Designs restrained, realistic camera motion trajectories per room type.
- **Supported Motions:** Slow Forward, Slow Backward, Subtle Dolly, Smooth Pan Left/Right, Gentle Orbit, Static Subtle Motion, Exterior Forward.
- **Safety Constraints:** Uses direct prompt constraints to preserve furniture, walls, geometry, and lighting while discouraging morphing, warping, appearing people/text/logos, and architectural hallucinations. The current Veo 3.1 integration does not send a separate negative-prompt field.

### 2.4 Video Diffusion Engine (Gemini Veo 3.1)
- **Role:** Generates 4-second video clips for each individual scene using image-to-video diffusion.
- **Validation:** Every generated clip is verified using FFprobe for valid headers, H.264 video streams, exact duration, and uncorrupted frames.
- **Free-tier controls:** One remote submission is active at a time by default. Submissions are paced, transient 429 responses use bounded exponential backoff, and quota failures are marked paused.
- **Recovery:** Queued and interrupted jobs are persisted in project generation metadata and re-queued during application startup.

### 2.5 Local Slideshow Fallback
- **Role:** Produces a usable walkthrough without a remote video provider.
- **Behavior:** Reads planned source images, preserves aspect ratio with letterboxing, renders a short MP4 locally, and publishes it through the final-video endpoints.
- **Trade-off:** This is a deterministic slideshow, not generative camera motion.

### 2.6 FFmpeg Video Assembler
- **Role:** Stitches generated clips into a unified property walkthrough MP4.
- **Normalization:** Standardizes resolution (720p/1080p), frame rate (24fps), and pixel format (`yuv420p`).
- **Transitions:** Restrained straight cuts and short crossfades (0.4s).
- **Outdated Plan Tracking:** Calculates SHA-256 fingerprint of the generation plan. If the plan changes after assembly, the video is marked `is_outdated`.

### 2.7 Immersive Viewer Engine
- **Role:** Provides interactive inspection of property scenes.
- **360° Spherical Canvas:** Projects 2:1 aspect ratio equirectangular panoramas with yaw/pitch drag rotation, FOV zooming, auto-turn, and wrap-around seam handling.
- **High-Res 2D Pan/Zoom:** Bounded hardware-accelerated pan/zoom for standard perspective photos without false spherical distortion.

### 2.8 Evaluation & Technical Quality Module
- **Role:** Verifies prototype performance and records human reviews.
- **6 Dimensions:** Visual Quality, Property Consistency, Scene Ordering, Motion Quality, Temporal Stability, Walkthrough Usefulness.
- **Automated Checks:** Validates completeness of scene analyses, clip generation, video assembly, and plan synchronization.

---

## 3. Storage Hierarchy

```
backend/storage/projects/<project_id>/
├── project.json              # Project session metadata & image array
├── uploads/                  # Original uploaded photographs (untouched)
│   ├── img_01_living_room.jpg
│   └── img_02_kitchen.jpg
├── processed/                # Normalized analysis images & web thumbnails
│   ├── thumb_img_01.jpg
│   └── norm_img_01.jpg
├── plan.json                 # Current versioned walkthrough plan
├── generation.json           # Persisted scene jobs, retries, pauses, and clip metadata
├── clips/                    # Individual scene video clips
│   └── clip_scene_01.mp4
├── final/                    # Assembled walkthrough MP4 & metadata
│   ├── walkthrough.mp4
│   └── metadata.json
└── evaluation/               # Human reviews & evaluation metrics
    ├── evaluations.json
    └── scene_reviews.json
```
