# Comprehensive End-to-End Live Demonstration Workflow

This guide provides a suggested demonstration workflow for the minor project presentation, faculty viva, and live technical defense. Exact labels and results may vary with the current checkout, input images, API availability, and provider quota.

---

## 1. System Initialization & Startup

### Step A: Configure Environment Variables
Verify `.env` configuration in `backend/.env` and `frontend/.env.local`:
```env
# backend/.env
PROJECT_NAME="Image-to-Video Walkthrough Generation"
VERSION=0.6.0
API_PREFIX=/api
STORAGE_DIR=storage
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

AI_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key_here
AI_MODEL=gemini-3.8-flash

VIDEO_PROVIDER=gemini_veo
VIDEO_API_KEY=your_gemini_api_key_here
VIDEO_MODEL=veo-3.1-generate-preview
MAX_CONCURRENT_GENERATIONS=1
VIDEO_SUBMISSION_INTERVAL_SECONDS=10
VIDEO_RATE_LIMIT_RETRY_ATTEMPTS=3
VIDEO_RATE_LIMIT_BACKOFF_SECONDS=15
```

```env
# frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Step B: Launch Backend Server
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
*Verify:* Navigate to `http://localhost:8000/api/health` and confirm the response contains `data.status: "healthy"` and `data.service: "walkthrough-backend"`.

### Step C: Launch Frontend Client
```bash
cd frontend
npm run dev
```
*Verify:* Open `http://localhost:3000/studio`.

---

## 2. The 17-Step Live Demonstration Flow

### Step 1 — Open the Application
- Open browser at `http://localhost:3000/studio`.
- Point out the top header, phase tracker bar (Phases 1 to 5/6), and active backend health indicator (`System Online`).

### Step 2 — Create New Property Project
- Enter the project title in the property form (e.g., *"Luxury Architectural Villa"*).
- Explain that a session directory (`storage/projects/<project_id>`) is created with atomic metadata persistence.

### Step 3 — Upload Property Images
- Drag and drop 5–8 realistic property photographs into the Dropzone (e.g., Exterior, Foyer, Living Room, Kitchen, Bedroom, Bathroom, Balcony).
- Point out the batch upload progress indicator.

### Step 4 — Show Image Validation
- Show that each image undergoes byte-level Pillow format verification (JPEG, PNG, WebP), minimum resolution check (≥ 512×512 px), size limit enforcement (≤ 20 MB), and bitwise SHA-256 deduplication.
- Highlight derived thumbnail generation.

### Step 5 — Run Scene Understanding
- Click **"Proceed to Scene Analysis"** or Phase 2 in the tracker.
- Click **"Analyze All Scenes with Gemini Vision"**.
- Explain that Google Gemini 2.5 Flash processes each photograph multimodally.

### Step 6 — Show Detected Scene Information
- Review the generated scene cards:
  - Detected room category (e.g. Living Room, Kitchen, Bedroom).
  - Lighting condition (Natural daylight, warm artificial fixtures).
  - Key architectural fixtures (island counter, hardwood floors, ceiling beams).
  - Detected doorway/connection clues.
  - Image quality metrics (sharpness, contrast, illumination).

### Step 7 — Review and Correct Scene Labels
- Demonstrate manual correction: click the room dropdown on a card and change a label (e.g. change *"Living Room"* to *"Formal Living Area"*).
- Point out the *"User Confirmed"* badge, proving that human oversight overrides AI model predictions.

### Step 8 — Generate Walkthrough Plan
- Advance to Phase 3 **"Walkthrough Planning"**.
- Explain that the `OrderingEngine` constructs a directed scene graph and applies topological sorting.

### Step 9 — Show Scene Ordering
- Point out the logical progression:
  1. `Exterior Front` → 2. `Entrance Foyer` → 3. `Living Room` → 4. `Kitchen` → 5. `Master Bedroom` → 6. `Bathroom` → 7. `Balcony`.
- Show that the rationale for each transition is explicitly documented.

### Step 10 — Show Camera-Motion Planning
- Show the conservative camera trajectory assigned to each room:
  - *Slow Forward Movement* for entrances.
  - *Smooth Pan Left/Right* for kitchens.
  - *Subtle Dolly* for bedrooms.
  - *Static Subtle Motion* for compact bathrooms.
- Highlight the direct preservation and anti-distortion prompt constraints used by the Veo 3.1 integration. It does not send a separate negative-prompt field.

### Step 11 — Generate Video Clips
- Advance to Phase 4 **"Video Generation"**.
- Select only the scenes needed for the demonstration, then click **"Generate Selected"**.
- Explain that one Gemini Veo request is submitted at a time with pacing to reduce free-tier bursts.
- If the provider quota is exhausted, the affected job is paused instead of being retried indefinitely.

### Step 12 — Show Generated Scene Clips
- Inspect individual generated scene clips in the browser player.
- Point out that every clip is probed and decoded before assembly. The configured target is 24fps/H.264 and the provider target is 4 seconds, but measured metadata can differ and should be read from the job result.
- If Veo is unavailable, click **"Use Image Slideshow"** to create a local, aspect-ratio-preserving MP4 without an API call.

### Step 13 — Assemble Final Walkthrough
- Advance to Phase 5 **"Walkthrough & Review"**.
- Enable or disable the Title Card intro option (1.5s).
- Click **"Assemble Walkthrough Video"**.
- Explain that FFmpeg normalizes all clips to 1280×720/24fps and applies restrained straight cuts or short crossfades (default 0.35s).

### Step 14 — Play Final Walkthrough
- Play the assembled walkthrough in the custom HTML5 video player.
- Demonstrate timecode seekbar, volume control, fullscreen, and click **"Download (.mp4)"** to export the video.

### Step 15 — Open Immersive Scene Viewer
- Switch the top toggle from `[ 🎬 Cinematic Walkthrough ]` to `[ 🌐 Immersive Scene Viewer ]`.
- For standard perspective photos: demonstrate high-resolution 2D bounded pan/zoom.
- For genuine 2:1 panoramas: demonstrate interactive 360° spherical canvas rotation (yaw/pitch dragging, FOV zoom, auto-turn).
- Toggle between **"Source Photo"** and **"Generated Clip"** to show fidelity.

### Step 16 — Run Evaluation
- Scroll to the **"Walkthrough Evaluation & Quality Audit"** section.
- Review the 6 dimensions (Visual Quality, Property Consistency, Scene Ordering, Motion Quality, Temporal Stability, Practical Usefulness).
- Select star ratings (1–5 scale), enter reviewer notes, and submit.
- Show updated arithmetic aggregate averages in the evaluation summary.

### Step 17 — Show Final Evaluation Report
- Click **"Technical Report"** button.
- Review the automated system verification checks and explain any failed or incomplete check rather than assuming every check will pass.
- Click **"Download .txt"** to export the standardized technical audit report.
