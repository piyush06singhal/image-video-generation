# End-to-End Demonstration Guide

This guide provides the exact steps to demonstrate the complete 6-Phase application from a clean environment.

---

## 1. Environment Setup & Startup

### Step 1: Start the Backend Server
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
*Backend URL:* `http://localhost:8000`  
*Swagger API Documentation:* `http://localhost:8000/docs`  
*Health Endpoint:* `http://localhost:8000/api/health`

### Step 2: Start the Frontend Application
```bash
cd frontend
npm install
npm run dev
```
*Frontend URL:* `http://localhost:3000`

---

## 2. End-to-End Walkthrough Demonstration Flow

### Step 1: Create Project & Upload Property Photos (Phase 1)
1. Open `http://localhost:3000/studio`.
2. Enter a property title (e.g. *Modern Architectural Residence*).
3. Drag and drop 5–8 realistic property photos representing:
   - Exterior Front
   - Foyer / Entrance
   - Living Room
   - Gourmet Kitchen
   - Master Bedroom
   - Bathroom
   - Balcony / Terrace
4. Verify that each uploaded photograph is validated (Pillow check, dimensions ≥ 512x512, format JPEG/PNG/WebP, SHA-256 deduplication).

### Step 2: Multimodal Scene Understanding (Phase 2)
1. Click **"Proceed to Scene Analysis"** or navigate to Phase 2.
2. Click **"Analyze All Scenes with Gemini Vision"**.
3. Inspect the extracted structured room metadata:
   - Scene Type (Living Room, Kitchen, Bedroom, etc.)
   - Architectural & Visual Features
   - Natural & Artificial Lighting Conditions
   - Visible Doorways / Connections
   - Confidence Score & Image Quality Metrics
4. Test manual correction by updating a room label or category if desired.

### Step 3: Walkthrough Route & Camera Planning (Phase 3)
1. Navigate to Phase 3 **"Walkthrough Planning"**.
2. Observe the automatic topological route ordering:
   - Exterior → Entrance → Living Room → Kitchen → Bedroom → Bathroom → Balcony.
3. Inspect the conservative camera motion trajectory assigned to each scene (e.g. Slow Forward, Gentle Pan Left, Smooth Dolly).
4. Reorder scenes or customize camera prompts if needed, then click **"Save Custom Plan"**.

### Step 4: Real Image-to-Video Clip Generation (Phase 4)
1. Navigate to Phase 4 **"Clip Generation"**.
2. Click **"Generate All Scene Video Clips"**.
3. Watch the progress indicators as each scene's clip is synthesized via generative video diffusion.
4. Preview individual generated scene video clips directly in the browser player.

### Step 5: Final Video Assembly (Phase 5)
1. Navigate to Phase 5 **"Walkthrough & Review"**.
2. Choose assembly settings (Title Card Intro enabled/disabled, ambient audio track).
3. Click **"Assemble Walkthrough Video"**.
4. The FFmpeg engine normalizes all clips (uniform H.264 / 24fps), applies restrained transitions (cuts and 0.4s crossfades), and produces `walkthrough.mp4`.
5. Play the full unified walkthrough video in the custom player and test the **"Download (.mp4)"** button.

### Step 6: Immersive Scene Viewer & Quality Evaluation (Phase 6)
1. Switch to **`[ 🌐 Immersive Scene Viewer ]`** mode.
2. Navigate between rooms using the scene stepper.
3. For equirectangular 360° panoramas: test yaw/pitch drag, FOV zoom, and auto-rotation.
4. For standard perspective photos: test high-res 2D pan/zoom.
5. Toggle between **"Source Photo"** and **"Generated Clip"**.
6. Assign per-scene quality reviews (Acceptable / Needs Review / Failed) and defect tags.
7. Fill out the **6-Dimension Evaluation Form** and click **"Submit Evaluation Score"**.
8. Click **"Technical Report"** to inspect automated system verification checks and download the `.txt` audit report.

---

## 3. Automated Backend Test Execution

Run the complete 51-test suite to verify all subsystem invariants:
```bash
cd backend
./venv/bin/pytest tests/ -v
```
All 51 unit and integration tests will execute and report 100% PASS.
