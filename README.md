# CinéEstate: Image-to-Video Walkthrough Generation for Real Estate

[![Backend](https://img.shields.io/badge/Backend-FastAPI_0.115+-009688.svg?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![Frontend](https://img.shields.io/badge/Frontend-Next.js_16_(React_19)-000000.svg?style=flat-square&logo=next.js)](https://nextjs.org)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB.svg?style=flat-square&logo=python)](https://python.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0%2B-3178C6.svg?style=flat-square&logo=typescript)](https://www.typescriptlang.org)
[![Test Suite](https://img.shields.io/badge/Tests-run%20locally%20with%20pytest-22c55e.svg?style=flat-square)]()
[![License](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](LICENSE)

An end-to-end, multi-stage generative pipeline and interactive inspection platform that transforms unordered collections of 2D real estate photographs into coherent, architecturally ordered, cinematographic video walkthroughs and immersive spatial viewing experiences.

---

## Executive Summary

Traditional real estate listings rely on disconnected photo galleries that require buyers to mentally reconstruct spatial layouts, or expensive 3D Matterport/LIDAR hardware requiring hundreds of multi-view captures. 

**CinéEstate** bridges this gap using an academic vision-language and video diffusion architecture:
1. **Automated Structural & Semantic Ingestion:** Ingests unordered photographs within configurable project limits, performs byte-level integrity checks, SHA-256 deduplication, and panorama detection signals.
2. **Multimodal Scene Understanding (VLM):** Uses Google Gemini 2.5 Flash to classify architectural room types, evaluate lighting, detect door connections, and quantify image quality.
3. **Topological Scene Graph Planning:** Constructs a directed graph and applies deterministic ordering heuristics to suggest a natural walkthrough flow (`Exterior` → `Foyer` → `Living` → `Kitchen` → `Private Quarters` → `Outdoor`). The planner does not create source images for missing rooms.
4. **Diffusion-Based Motion Synthesis:** Translates planned camera trajectories (e.g. slow forward dollies, kitchen pans) into photorealistic 4-second video clips via Gemini Veo with direct preservation and anti-distortion constraints. The current Veo 3.1 integration does not send a separate negative-prompt field.
5. **Deterministic Video Normalization & Assembly:** Standardizes video streams with FFmpeg using proportional letterbox padding and configurable cuts or short crossfades.
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
│   │ Phase 4: Cinematic Clip Rendering │               │ Phase 3: Walkthrough Planning & Trajectory Graph           │   │
│   │ • Pluggable I2V Engine Selection  │◀──────────────│ • Directed Topological Scene Graph Construction            │   │
│   │ • Prompt grounding & safety locks │ Camera Prompts│ • Hierarchy Sorting (Exterior ➔ Living ➔ Private ➔ Outdoor)│   │
│   │ • Asynchronous execution queue    │  & Parameters │ • Conservative Camera Motion Planner (Pan/Dolly/Drift)     │   │
│   │ • Video stream probing/verification│               │ • Plan Fingerprinting & SHA-256 Versioning                 │   │
│   └─────────────────┬─────────────────┘               └────────────────────────────────────────────────────────────┘   │
│                     │ Per-Scene                                                                                        │
│                     │ MP4 Clips                                                                                        │
│                     ▼                                                                                                  │
│   ┌───────────────────────────────────┐               ┌────────────────────────────────────────────────────────────┐   │
│   │ Phase 5: Normalization & Assembly │               │ Phase 6: Immersive Viewer & Evaluation Suite               │   │
│   │ • FFmpeg cover-crop conform       │──────────────▶│ • 360° Spherical Equirectangular Canvas Viewer            │   │
│   │ • Configurable aspect/res/fps     │ Walkthrough   │ • 2D Ultra High-Res Bounded Pan/Zoom Mode                  │   │
│   │ • Branded cards, labels, score    │     Video     │ • 4-Point Automated Verification Checks                    │   │
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
- **Topological Sorting:** Builds a directed adjacency graph and applies an architectural ordering heuristic from public entryways to private quarters.
- **Conservative spatial scope:** Intermediate rooms omitted by the user are not added as separate planned scenes; transitions between available scenes use the configured transition.
- **Conservative Camera Motion Selection:** Maps scene types to restrained camera trajectories (e.g. forward dolly for foyers, lateral pans for kitchens, subtle static drift for bathrooms) while using direct preservation and anti-distortion constraints in the Veo prompt. The current Veo 3.1 integration does not send a separate negative-prompt field.

### Phase 4: Image-to-Video Generation
- **Pluggable Provider Architecture:** `VIDEO_PROVIDER` selects the motion engine at runtime (`auto` | `json2video` | `gemini_veo` | `kenburns`). Providers share one contract, so the pipeline is identical regardless of engine.
- **Generative Video Synthesis (Veo):** Google Gemini Veo 3.1 synthesizes 4-second clips from single static photographs guided by the scripted motion prompts and direct preservation constraints. Safety prompt engineering uses direct preservation and anti-distortion instructions (`preserve furniture, walls, lighting, and geometry; no distortion`) to reduce structural artifacts. The current Veo 3.1 integration does not send a separate negative-prompt field.
- **Local Cinematic Motion (Ken Burns):** Renders a genuine camera move — pan, push-in, pull-back, subtle drift — over the *real* photograph using a sub-pixel affine "virtual camera" in OpenCV and FFmpeg. Runs on CPU with no API, no quota and no cost, and is deterministic, so the property can never be hallucinated or refurnished.
- **Cloud Rendering (JSON2Video):** Composites the real photos with pan/zoom, easing and cross-dissolves through the JSON2Video rendering API — generous free tier (600s of rendered output) and no local GPU/CPU load. Requires `JSON2VIDEO_API_KEY` and a publicly reachable `PUBLIC_BASE_URL`, because the renderer downloads each source photo by URL.
- **Graceful Degradation:** Any remote provider that is rate-limited, out of quota, content-blocked, timed out or misconfigured automatically falls back to the local renderer, so a walkthrough is always produced.
- **Video Stream Verification:** Probes and decodes each generated clip before assembly to confirm it is readable and has expected metadata such as codec, resolution, and frame rate.

### Phase 5: Video Normalization & Multi-Clip Assembly
- **Frame Conforming:** Every clip is *cover-cropped* (scaled to fill, centre-cropped) to the project's exact target frame, so no black bars ever survive into the delivered video. The target is `aspect_ratio × resolution` (for example `9:16` at `720p` → $720\times 1280$) rather than a fixed $1920\times 1080$ canvas, and the frame rate is configurable ($24/30/60$).
- **Branded Intro & Outro Cards:** Renders opening and closing cards over a blurred, slowly drifting plate taken from the property's own photography, with gold-rule typography — rather than the flat black card this used to emit.
- **Room Label Overlays:** Burns a fading lower-third room name onto each scene clip so viewers always know which space they are looking at.
- **Cinematic Grade:** Applies the chosen colour treatment (warm luxury / cool modern / cinematic teal / noir) plus optional vignette and film grain in a single encode pass, so photographs read as footage.
- **Transition Stitching:** Executes the selected transition between every pair of shots — straight cut, cross dissolve, fade-through-black, slide or wipe — at the configured duration, using multi-input FFmpeg `xfade` graphs. If the transition graph fails the render degrades to straight cuts and logs it loudly rather than silently pretending nothing happened.
- **Royalty-Free Score:** Synthesises a background bed from sine partials with a slow amplitude swell, low-pass, echo and matched fades — nothing is downloaded and nothing is licensed. A score failure degrades to a silent cut instead of failing the render.
- **Honest Output Metadata:** The final metadata reports the audio codec actually present in the container and the render-options fingerprint used, instead of hardcoding `audio_codec: null`.
- **Invalidation Tracking:** Compares the plan SHA-256 hash *and* the render-options fingerprint against the assembled result, so changing the look (or the plan) flags the existing MP4 as outdated — and reverting to the settings a cut was built with makes it valid again.

### Phase 6: Immersive Viewer & Technical Evaluation
- **Dual-Mode Inspection:** Interactive HTML5 Canvas equirectangular spherical viewer for 360° panoramas and bounded high-res 2D pan/zoom for perspective photos.
- **Automated Verification Matrix:** Non-subjective server-side checks for scene analysis completion, clip availability, video stream integrity, and plan synchronization.
- **Standardized Human Evaluation:** 6-axis scoring rubric ($1.0$ to $5.0$) paired with scene-level defect flags (`geometry_distortion`, `flickering`, `unnatural_motion`, etc.) and exportable technical audit reports.

---

## Cinematic Render Options

One persisted, per-project configuration (`render_options.json`) controls how a walkthrough
looks, and both Phase 4 and Phase 5 read it, so a regenerate/reassemble reproduces the same
style without re-sending the form.

| Area | Controls |
| :--- | :--- |
| **Output frame** | Aspect ratio (`16:9` / `9:16` / `1:1`), quality tier (`720p` / `1080p` / `1440p`), frame rate (`24` / `30` / `60`) |
| **Pacing & motion** | Seconds per room, motion intensity (subtle / balanced / bold), per-room camera variety |
| **Depth & realism** | 2.5D depth parallax, motion blur |
| **Transitions** | Style (hard cut / cross dissolve / motion dissolve / blur dissolve / fade-through-black / slide / wipe) and duration |
| **Titles & overlays** | Intro card (+ custom headline and length), outro card, burned-in room labels, room counter & tour progress, brand mark |
| **Look** | Colour grade (warm luxury / golden hour / cool modern / cinematic teal / noir), vignette, film grain, highlight halation, cinematic bars |
| **Score** | Enable/disable, mood (ambient / uplifting / minimal piano), level. Every cut carries a synthesised whoosh, the first shot a riser, the end card a button |

Five built-in presets (`cinematic_luxury`, `modern_minimal`, `energetic_reel`,
`documentary_tour`, `quick_draft`) apply a coherent set of values in one click; individual
controls can then be adjusted. The studio exposes all of this in a **Cinematic Settings**
panel in Phase 4 and Phase 5, and the API mirrors it (`GET`/`PATCH
/api/projects/{id}/render-options`, `GET /api/projects/render-options/presets`).

Changing an option that reshapes the clips (length, frame shape, fps, motion) marks the
existing clips stale so they are regenerated on the next generate; changing a look-only
option marks the assembled video outdated so it is reassembled. Both are reported to the UI
rather than applied silently.

---

## Production Value

A camera move over a photograph looks like a slideshow unless the shot carries the cues a
real camera produces. The engine builds those cues explicitly.

| Feature | What it does | Why it matters |
| :--- | :--- | :--- |
| **2.5D depth parallax** | A monocular depth model (Depth Anything V2 Small, ONNX, run locally) estimates how far away each pixel is; the virtual camera then moves near pixels further than far ones | Without it, everything in the frame moves as one rigid sheet — which is exactly the effect users read as “a panning photo”. Measured on a real room: near-plane motion 16 px vs far-plane 3 px, against 9 px vs 6 px for the flat camera |
| **Motion blur** | Frames are accumulated over a trailing shutter window | Real footage blurs during fast movement; it is one of the strongest “this is a camera, not a still” cues |
| **Kinetic title cards** | The headline arrives with loose letter-spacing that tightens, the gold rule wipes outward, a soft light sweep crosses the plate, and the whole card fades up from black | A static card with text on it reads as a JPEG; this reads as a title sequence |
| **Animated lower-thirds** | Room name slides into place, with a position counter (“03 / 08”) and a gold tour-progress line | Tells a viewer where they are in the property, which is most of what separates a listing clip from a home video |
| **Highlight halation** | Only pixels above a measured gate feed the glow, which is a tight vertical blur smeared wide horizontally and screened back — the anamorphic bleed of a fast lens | The previous version screened a blurred copy of the *whole* frame, which left the picture ~30% softer than the source photograph and lifted the shadows into haze. Measured on a real 1080p interior: detail **19.0** without it, **17.5** with it, and **10.5** for the version it replaced; shadow floor 15 → 17, against **46** for the version it replaced |
| **Filmic colour** | `curves` gives a per-channel tonal shape — shadows lifted off true black, mids separated, highlights rolled off below clipping — plus split-toning and `vibrance` | The old grade darkened a well-exposed interior by ~30 luma levels and crushed 2% of the frame to black. A frame that is dimmer, with black corners and black bars, is exactly what reads as *diluted* |
| **Composed score** | A small procedural composer writes chords, a bass line, an arpeggio, soft percussion and a Schroeder reverb tail, then loudness-normalises | The score used to be a single held drone with no pulse. A bed with movement is what makes the cut feel produced |
| **Sound design on the cuts** | A synthesised whoosh lands on every transition, a riser on the first shot, a low button on the end card — mixed from the assembly's own cut positions | Music alone does not make an edit feel produced. Measured on a finished cut: the five noisiest moments in the whole mix are exactly the five cuts, 21–30× the median spectral flatness |
| **Continuous camera** | The ease compressed into the middle of a shot used to park the camera for the first and last tenth of every clip, so the cut read stop-start. Motion now begins almost at once and bleeds off speed, with a two-tone handheld float instead of a single periodic sway | A perfectly periodic wobble reads as machine motion; a stalled camera next to a crossfade reads as a slideshow |

Everything here is generated locally and deterministically: no licensed audio, no stock
footage and no per-render cost. The depth model is fetched once (see the install section) and
is deliberately **not** committed, since it is ~100 MB. If it is missing, or `onnxruntime` is
unavailable, the renderer falls back to a flat camera move instead of failing — so the
pipeline still produces a walkthrough out of the box.

**Honest limitations.** The score is procedurally composed, not a licensed recording. The
`kenburns` and `json2video` engines move a camera over the real photograph, so there is no
newly generated footage — motion is a cinematic camera move with real parallax, not a walk
into the room, and there are no people; only `gemini_veo` synthesises pixels, and it can
invent furniture. `gemini_veo` ignores frame size, frame rate and grade (the assembler
applies those afterwards). Depth is monocular, so extreme close-ups can smear at the
disocclusion between planes; `json2video` needs a publicly reachable `PUBLIC_BASE_URL` so its
renderers can fetch the source photos, and its cloud canvas is clamped to Full HD.

---

## Academic Scope & Technical Boundaries

To maintain scientific integrity and realistic evaluation bounds, CinéEstate operates under explicit architectural principles:

| Principle | Architectural Decision & Defense |
| :--- | :--- |
| **Topological Graph vs. 3D Reconstruction** | Constructs a topological scene graph rather than attempting dense Structure-from-Motion (SfM), NeRF, or 3D Gaussian Splatting (3DGS). This avoids metric reconstruction, but output quality still depends on the number, coverage, and quality of uploaded photographs. |
| **Conservative spatial scope** | The system plans and renders uploaded scenes only. It does not generate separate clips for unphotographed intermediate rooms; provider-generated motion can still contain visual artifacts. |
| **Generative vs. Plate-Based Motion** | Diffusion providers (`gemini_veo`) synthesize pixels and can therefore drift from the listing — invented furniture, warped geometry, changed finishes. Plate-based providers (`json2video`, `kenburns`) move a virtual camera over the real photograph, so the result is pixel-exact by construction. Accuracy and "wow factor" are a trade-off the operator selects with `VIDEO_PROVIDER`. |
| **Aspect Ratio: Fill vs Preserve** | The *video* pipeline cover-crops to the requested frame so output never contains black bars — the right choice for a vertical reel, at the cost of cropping landscape photographs. The *viewer* (Phase 6) preserves full source geometry. Choose `16:9` to retain the whole frame; a `9:16` render from landscape photographs is a deliberate centre crop. |
| **Equirectangular Projection Boundaries** | True 360° equirectangular panoramas are projected onto a spherical canvas; standard perspective photos remain in 2D to prevent false spherical warping. |

---

## Evaluation Framework & Benchmark Criteria

The platform integrates a standardized evaluation rubric and objective verification engine:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 Evaluation Framework                                   │
├──────────────────────────────────────────┬─────────────────────────────────────────────┤
│ 1. Automated Pipeline Verification       │ 2. 6-Axis Human Evaluation Rubric (1.0-5.0) │
│ • Scene Analysis Coverage (reported)     │ • Visual Quality & Realism (target: ≥ 4.0)  │
│ • Elementary Clip Availability (reported)│ • Property Consistency (target: ≥ 4.0)      │
│ • Video Stream Readability                │ • Scene Sequence & Flow (target: ≥ 4.5)     │
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
│   │   ├── PropertyForm.tsx / Dropzone.tsx # Image upload and project setup
│   │   ├── SceneResultsView.tsx       # AI scene classification & quality audit
│   │   ├── WalkthroughPlanView.tsx    # Interactive plan & camera planner
│   │   ├── GenerationView.tsx         # Queued video generation and fallback controls
│   │   ├── FinalWalkthroughView.tsx   # Video player & FFmpeg assembly controls
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
│   │   │   ├── generation.py          # Video generation jobs and status schemas
│   │   │   └── evaluation.py          # Verification & review schemas
│   │   └── services/                  # Business logic services
│   │       ├── image_preprocessor.py  # Validation, EXIF & multi-signal pano detection
│   │       ├── scene_analyzer/        # Gemini 2.5 Flash VLM inference
│   │       ├── walkthrough_planner/   # Graph ordering, camera & transition planning
│   │       ├── video_generation/      # Gemini Veo provider, pacing and recovery
│   │       ├── local_slideshow_service.py # No-API image slideshow fallback
│   │       ├── video_assembler/       # FFmpeg probe, normalize, title, concat
│   │       └── evaluation_service.py  # Verification checks & audit report generation
│   ├── storage/projects/              # Isolated local project filesystem storage
│   └── tests/                         # Unit and integration tests across all phases
│
├── docs/                              # Comprehensive Technical Documentation
│   ├── architecture.md                # In-depth subsystem architecture & data flows
│   ├── api.md                         # Complete REST API endpoint reference
│   ├── viva.md                        # Viva questions & technical answers
│   ├── future-upgrades.md             # Future upgrades and academic scope boundaries
│   ├── final-demo.md                  # End-to-end live demonstration guide
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

### Free-tier operation

The application is designed to remain usable when Gemini/Veo free-tier capacity is limited:

- Veo requests run one at a time by default.
- Submissions are paced and transient rate limits use exponential backoff.
- Quota failures pause the affected job instead of retrying indefinitely.
- Users can select only the scenes they need to generate.
- A local image-slideshow fallback can create a valid walkthrough without a video API call.

**Choosing a provider.** The free-tier wall is a *provider* problem, not a pipeline
problem, so Phase 4 is swappable:

| `VIDEO_PROVIDER` | Motion source | Cost / limits | Property accuracy |
| :--- | :--- | :--- | :--- |
| `gemini_veo` | Generative diffusion (Veo) | Hardest free tier; 1 request at a time | Diffusion can invent furniture, geometry and finishes |
| `json2video` | Cloud render of the real photos (pan/zoom + transitions) | Free tier ≈ 600s of render | Exact — pixels are the actual listing |
| `kenburns` | Local render of the real photos (OpenCV + FFmpeg) | Free, unlimited, offline | Exact — pixels are the actual listing |
| `auto` (default) | Best configured remote, local fallback | — | Degrades rather than failing |

Run `VIDEO_PROVIDER=kenburns` for a fully offline walkthrough with zero API calls, or
set `JSON2VIDEO_API_KEY` + `PUBLIC_BASE_URL` to offload rendering to the cloud. In
`auto` mode a quota, rate-limit, content-block or misconfiguration error degrades the
affected clip to the local renderer instead of failing the job.

Free-tier quotas are provider-controlled and cannot guarantee unlimited or immediate video generation. See [`docs/future-upgrades.md`](docs/future-upgrades.md) before onboarding multiple users.

---

### 1. Backend Installation & Execution

```bash
# Navigate to backend directory
cd backend

# Fetch the local depth model used for 2.5D parallax (~100MB, not committed)
mkdir -p models
curl -L -o models/depth_anything_v2_small.onnx \
  https://huggingface.co/onnx-community/depth-anything-v2-small/resolve/main/onnx/model.onnx

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

The project includes an automated test suite covering all 6 phases:

```bash
cd backend
./venv/bin/pytest tests/ -v
```

The exact test count and timing depend on the current checkout. The command above is the source of truth.

Note: `API_ACCESS_KEY` is a *deployment* guard read from `backend/.env`. The test suite
neutralises it by default so a developer's local key does not turn every API test into a
401; `tests/test_api_access_key.py` opts back in explicitly to cover the guard itself.

To run the frontend production build verification:
```bash
cd frontend
npm run build
```

## Vercel deployment

The Next.js frontend and FastAPI backend can be deployed as separate Vercel projects.
Follow [`docs/deployment-vercel.md`](docs/deployment-vercel.md) for the exact root
directories, environment variables, and verification commands.

The frontend is Vercel-ready. The backend has a Vercel adapter for academic demos and
API experimentation, but reliable public video generation still requires durable media
storage and a managed worker/container because Vercel serverless files and in-process
background jobs are not persistent.

---

## Technical Documentation Index

For exhaustive technical reference and evaluation preparation, consult the `/docs` directory:

| Document | Description |
| :--- | :--- |
| [`docs/architecture.md`](file:///Users/piyushsinghal/Documents/Projects/image-video/docs/architecture.md) | Deep architectural specifications, module responsibilities, and data models. |
| [`docs/api.md`](file:///Users/piyushsinghal/Documents/Projects/image-video/docs/api.md) | Complete REST API endpoint reference with request/response payloads. |
| [`docs/viva.md`](file:///Users/piyushsinghal/Documents/Projects/image-video/docs/viva.md) | Viva and technical-defense questions with implementation-grounded answers. |
| [`docs/future-upgrades.md`](file:///Users/piyushsinghal/Documents/Projects/image-video/docs/future-upgrades.md) | Future upgrades, academic boundaries, scope constraints, and explicit non-goals. |
| [`docs/final-demo.md`](file:///Users/piyushsinghal/Documents/Projects/image-video/docs/final-demo.md) | End-to-end live demonstration and evaluation script. |
| [`docs/evaluation.md`](file:///Users/piyushsinghal/Documents/Projects/image-video/docs/evaluation.md) | Evaluation metric formulas, automated verification rules, and rubric scoring. |
| [`docs/results.md`](file:///Users/piyushsinghal/Documents/Projects/image-video/docs/results.md) | Reproducible test commands, result-recording template, and evaluation guidance. |
| [`docs/screenshots.md`](file:///Users/piyushsinghal/Documents/Projects/image-video/docs/screenshots.md) | 13 ordered screenshot captures for documentation and report inclusion. |
| [`docs/presentation-outline.md`](file:///Users/piyushsinghal/Documents/Projects/image-video/docs/presentation-outline.md) | 18-slide academic presentation structure with talking points. |

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
