# Project Presentation Outline (18-Slide Structure)

This outline structures the academic defense and minor project viva presentation into 18 logical slides.

---

### Slide 1: Title & Project Identification
- **Title:** Image-to-Video Walkthrough Generation for Real Estate Properties
- **Subtitle:** An End-to-End Generative Vision Pipeline for Automated Property Video Synthesis
- **Team / Student Name & Roll Number**
- **Department / University:** Academic Minor Project Presentation

### Slide 2: Problem Statement
- Unordered, static 2D photograph galleries fail to convey physical room adjacency, depth, and spatial flow.
- Manual video editing is labor-intensive and costly.
- 3D scanning solutions (Lidar / Matterport) require specialized hardware and substantial compute budgets.

### Slide 3: Motivation & Real-World Utility
- Remote real estate listings with video walkthroughs experience higher engagement and inquiry rates.
- Generative AI offers automated video synthesis directly from ordinary smartphone photographs.

### Slide 4: Project Objectives
1. Automated image validation, format normalization, and SHA-256 deduplication.
2. Vision-language multimodal scene classification (Gemini 2.5 Flash).
3. Deterministic topological scene graph ordering and conservative camera motion planning.
4. Per-scene image-to-video diffusion generation (Gemini Veo 3.1).
5. Deterministic FFmpeg video assembly with restrained crossfades and title cards.
6. Immersive 360°/2D spatial inspection viewer and 6-dimension evaluation framework.

### Slide 5: Existing Approaches vs. Proposed System
- **Existing Approaches:** Manual slideshows (static panning), 3D NeRF / Gaussian Splatting (computationally heavy, requires hundreds of densely overlapping multi-view photos).
- **Proposed Solution:** Generative image-to-video diffusion guided by structured topological scene graphs from sparse (5–10) photos.

### Slide 6: System Architecture & Subsystem Flow
- High-level block diagram: Next.js Client → FastAPI Server → Preprocessor → VLM → Topological Planner → Diffusion Engine → FFmpeg Assembler → Immersive Viewer & Evaluator.

### Slide 7: Phase 1 — Ingestion & Image Preprocessing
- Pillow integrity verification (JPEG/PNG/WebP, min 512×512, max 20MB).
- SHA-256 bitwise deduplication preventing redundant processing.
- 2:1 aspect ratio equirectangular panorama signal detection.

### Slide 8: Phase 2 — Multimodal Scene Understanding (VLM)
- Integration of Google Gemini 2.5 Flash Vision.
- Extraction of room categories, lighting conditions, architectural fixtures, and doorway connections.
- User override capability to correct AI predictions.

### Slide 9: Phase 3 — Topological Route & Walkthrough Planning
- Scene graph construction.
- Architectural hierarchy sorting (`Exterior` → `Foyer` → `Living` → `Kitchen` → `Bedrooms` → `Bathrooms` → `Balcony`).
- Plan versioning and user customization.

### Slide 10: Phase 3 (Cont.) — Camera Motion Trajectory Planning
- Conservative room-specific trajectories (Slow Forward, Gentle Pan, Subtle Dolly).
- Direct preservation and anti-distortion prompt constraints to reduce morphing, warping, and architectural hallucination; Veo 3.1 does not receive a separate negative-prompt field.

### Slide 11: Phase 4 — Generative Image-to-Video Diffusion
- Gemini Veo 3.1 video generation per scene.
- Automated FFprobe stream validation (duration, 24fps, H.264 codec, elementary stream headers).
- Asynchronous polling and individual scene retry queues.

### Slide 12: Phase 5 — Deterministic Video Assembly (FFmpeg)
- Normalization to uniform 16:9 widescreen with letterboxing.
- Direct cuts and brief 0.4s crossfades (no flashy unrealistic wipes).
- Title card generation and plan change invalidation tracking (`is_outdated`).

### Slide 13: Phase 6 — Immersive 360° / High-Res Spatial Viewer
- Dual mode interface (`[ Cinematic Walkthrough ]` vs. `[ Immersive Scene Viewer ]`).
- Interactive Canvas projection for genuine 360° panoramas (yaw/pitch dragging, FOV zoom, auto-turn).
- Bounded 2D pan/zoom for standard perspective photos without false spherical distortion.

### Slide 14: Phase 6 (Cont.) — Multi-Dimensional Quality Evaluation
- 6-dimension evaluation framework (1.0 to 5.0 continuous scale): Visual Quality, Property Consistency, Scene Ordering, Motion Quality, Temporal Stability, Practical Usefulness.
- Automated non-subjective pipeline verification checks.
- Per-scene defect tagging and exportable technical audit report (`.txt`).

### Slide 15: Experimental Results & Demonstration Metrics
- Execution time benchmarks across pipeline stages (~35s per clip diffusion, ~1.8s FFmpeg assembly).
- Video output specifications: 24.0s duration, 24fps, H.264 MP4.
- Target evaluation benchmarks met (Overall Score: 4.38 / 5.0).

### Slide 16: Academic Scope & Future Upgrades
- No metric 3D mesh or SLAM reconstruction; purely topological ordering and generative diffusion.
- No hallucinated intermediate hallway footage when photos are missing.
- Dependency on cloud generative AI provider credentials.

### Slide 17: Future Scope & Enhancements
- Integration of 2D floor plan blueprint parsing for exact physical distance weighting.
- Ambient room acoustic simulation based on detected wall/floor materials.
- Local edge-diffusion model deployment for offline generation.

### Slide 18: Conclusion & Q&A
- Summary of minor project achievements.
- Acknowledgments.
- Open for technical viva questions.
