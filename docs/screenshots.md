# Recommended Screenshot Capture Checklist

This document details the 13 essential screenshots to capture for the project report, viva slide deck, and minor project demonstration.

---

### Screenshot 1: Landing Page & Architectural Overview
- **URL / View:** `http://localhost:3000/`
- **Key UI Elements to Show:** Hero headline (*"Transform Real Estate Photos into Coherent Cinematic Walkthroughs"*), feature highlights, glassmorphic pipeline cards, and the *"Launch Walkthrough Studio"* call to action.

### Screenshot 2: Studio Initialization & Property Configuration
- **URL / View:** `http://localhost:3000/studio` (Phase 1)
- **Key UI Elements to Show:** Top Studio Header, 5-phase tracker bar, Property Name input field (*"Modern Architectural Residence"*), and clean ivory luxury theme.

### Screenshot 3: Batch Image Upload & Ingestion Validation
- **URL / View:** `http://localhost:3000/studio` (Phase 1)
- **Key UI Elements to Show:** Drag-and-drop dropzone with active file badges, validation status indicators (dimensions, format, file size), and upload progress.

### Screenshot 4: Validated Property Image Grid
- **URL / View:** `http://localhost:3000/studio` (Phase 1 Completed)
- **Key UI Elements to Show:** Grid of 6 uploaded property photos with resolution labels, thumbnail previews, and the green *"Proceed to Scene Analysis"* button.

### Screenshot 5: Gemini Multimodal Scene Understanding
- **URL / View:** `http://localhost:3000/studio` (Phase 2)
- **Key UI Elements to Show:** Analyzed scene cards displaying detected room types (Living Room, Kitchen, Bedroom), natural/artificial lighting status, confidence scores, and extracted architectural features.

### Screenshot 6: Manual Scene Correction Override
- **URL / View:** `http://localhost:3000/studio` (Phase 2)
- **Key UI Elements to Show:** Room classification dropdown open, custom label editor, and *"User Confirmed"* badge overriding AI model predictions.

### Screenshot 7: Walkthrough Plan & Topological Route Ordering
- **URL / View:** `http://localhost:3000/studio` (Phase 3)
- **Key UI Elements to Show:** Ordered walkthrough sequence (01. Exterior → 02. Entrance → 03. Living Room → 04. Kitchen → 05. Master Suite → 06. Bathroom), ordering rationale explanations, and plan version indicator.

### Screenshot 8: Camera Motion Trajectory & Constraint Planner
- **URL / View:** `http://localhost:3000/studio` (Phase 3)
- **Key UI Elements to Show:** Camera motion selector pills (*Slow Forward Movement*, *Smooth Pan Left*, *Subtle Dolly*), duration badges, and direct preservation/anti-distortion prompt guidance.

### Screenshot 9: Video Diffusion Clip Generation Studio
- **URL / View:** `http://localhost:3000/studio` (Phase 4)
- **Key UI Elements to Show:** Per-scene generation progress cards, active job status, retry buttons, and thumbnail-to-video status indicators.

### Screenshot 10: Generated Scene Video Clip Previews
- **URL / View:** `http://localhost:3000/studio` (Phase 4 Completed)
- **Key UI Elements to Show:** Individual scene MP4 video players playing 4-second camera animations with duration, FPS (24fps), and resolution (720p) badges.

### Screenshot 11: Final Assembled Walkthrough Video Player
- **URL / View:** `http://localhost:3000/studio` (Phase 5 - Cinematic Mode)
- **Key UI Elements to Show:** Custom video player HUD (play/pause, seekbar, timecode `00:00 / 00:24`, volume, fullscreen), metrics strip (Duration: 24.0s, Codec: H.264, 6 scenes), and *"Download Walkthrough MP4"* button.

### Screenshot 12: Immersive 360° / High-Res Scene Inspector
- **URL / View:** `http://localhost:3000/studio` (Phase 5 - Immersive Mode)
- **Key UI Elements to Show:** 360° spherical Canvas viewport with rotation indicator, FOV zoom controls, auto-turn toggle, Source Photo vs. Generated Clip switcher, and mandatory scope disclaimer.

### Screenshot 13: Technical Quality Report & Evaluation Modal
- **URL / View:** `http://localhost:3000/studio` (Phase 5 / 6)
- **Key UI Elements to Show:** 6-dimension evaluation score summary bars (Visual Quality, Consistency, Ordering, Motion, Stability, Usefulness), per-scene defect tags, automated checks (PASS), and the formatted plain-text report export.
