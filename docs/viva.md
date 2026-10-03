# Comprehensive Viva & Technical Defense Guide

This document contains 26 core technical questions and precise, grounded answers based directly on the actual implementation of the **Image-to-Video Walkthrough Generation for Real Estate Properties** system.

---

### 1. What is the problem statement?
**Answer:** The project addresses the problem of converting an unordered set of 2D interior and exterior real estate photographs into a coherent, architecturally ordered, cinematographic video walkthrough and spatial inspection tool, without requiring manual video editing or full 3D scanning hardware.

### 2. Why is this problem useful for real estate?
**Answer:** Static photo galleries force potential buyers to mentally reconstruct room layouts and spatial relationships. Video walkthroughs provide immediate spatial context, depth, and flow, improving remote listing inspection and engagement without the high cost and specialized equipment of 3D lidar or Matterport scanning.

### 3. What is the input to the system?
**Answer:** A set of 5 to 15 unordered 2D digital photographs of a property (interior and exterior) in standard image formats (JPEG, PNG, WebP) with minimum resolution of 512×512 pixels.

### 4. What is the output of the system?
**Answer:**
1. A unified, normalized 16:9 H.264 MP4 property walkthrough video with restrained transitions.
2. An interactive spatial inspection viewer supporting both high-resolution 2D pan/zoom and 360° spherical projection for panoramic images.
3. A standardized quantitative and qualitative evaluation audit report.

### 5. Why is image ordering necessary?
**Answer:** Real estate photographs are typically captured and uploaded in arbitrary order. Random video concatenation causes spatial disorientation (e.g. jumping from a bathroom directly to an exterior driveway, then to a kitchen). Topological ordering ensures a natural, logical progression from exterior entrance to central living areas and private quarters.

### 6. How does the system understand the uploaded images?
**Answer:** The system uses vision-language model inference via Google Gemini 2.5 Flash (`backend/app/services/scene_analyzer/gemini_provider.py`), which analyzes each photograph to extract spatial classification, lighting conditions, architectural features, visible doorways, and quality metrics.

### 7. Which component performs scene understanding?
**Answer:** The `SceneAnalysisService` interfacing with the Google GenAI SDK (`gemini-2.5-flash`), supplemented by Pillow-based image preprocessing (`ImagePreprocessor`) for sharpness, illumination, and contrast analysis.

### 8. What is the role of the VLM (Vision-Language Model)?
**Answer:** The VLM acts as an automated architectural annotator. It converts raw pixel data into structured JSON metadata describing the room category, visual fixtures, natural/artificial lighting sources, and visible inter-room connection clues.

### 9. How is walkthrough ordering determined?
**Answer:** The `OrderingEngine` (`walkthrough_planner/ordering.py`) builds a directed scene graph using detected spatial hierarchies and applies deterministic topological sorting:
`exterior_front` → `entrance_foyer` → `living_room` / `dining_room` → `kitchen` → `hallway_corridor` / `stairs` → `master_bedroom` / `bedroom` → `bathroom` → `balcony_terrace` / `backyard_garden`.

### 10. How is camera motion selected?
**Answer:** The `CameraMotionPlanner` maps room categories to restrained, realistic trajectories (e.g. Slow Forward for foyers/living rooms, Gentle Pan Left/Right for kitchens, Subtle Dolly for bedrooms, Static Subtle Drift for bathrooms). The Veo 3.1 prompt uses direct preservation and anti-distortion constraints to reduce jarring rotations or warping.

### 11. What is the role of the image-to-video model?
**Answer:** The generative diffusion model (Google Gemini Veo 3.1) synthesizes short (4-second) video clips from single static photographs, applying direct preservation constraints and scripted camera motion prompts while preserving original room geometry and furniture.

### 12. Why are separate clips generated for each scene?
**Answer:** Generating individual per-scene clips isolates diffusion errors, prevents cross-room morphing artifacts, allows per-scene retry without re-rendering the entire property, and enables flexible re-ordering in the timeline.

### 13. Why is FFmpeg used in the pipeline?
**Answer:** FFmpeg (`video_assembler/ffmpeg_engine.py`) provides deterministic video processing: probing elementary streams, standardizing resolutions and framerates (H.264 / 24fps / `yuv420p`), generating title cards, and concatenating clips with crossfades.

### 14. How are the clips assembled?
**Answer:** The `VideoAssemblerService` normalizes all approved scene clips to uniform dimensions and framerate, generates an optional title card, applies approved transition filters (`straight_cut` or `short_crossfade`), and executes a multi-input filter-complex concatenation into a single `walkthrough.mp4`.

### 15. How does the system maintain visual consistency?
**Answer:**
1. Direct prompt constraints describing preservation of visible furniture, geometry, lighting, and restrained motion. The current Veo 3.1 integration does not send a separate negative-prompt field.
2. Conservative camera trajectories that avoid rapid perspective shifts.
3. Proportional letterboxing during normalization to avoid intentional geometric stretching.

### 16. What happens if the AI model fails or returns malformed output?
**Answer:** The backend validates provider and application responses and reports errors through the job state:
- In Scene Understanding: Malformed JSON falls back to a safe default classification (`unknown`) with diagnostic warnings, and the user can manually correct it via the UI.
- In Video Generation: Request timeouts or transient API errors are captured, logged, and placed in the persisted generation workflow; provider quota errors pause the job rather than retrying indefinitely.

### 17. What happens if one video clip fails to generate?
**Answer:** The assembly engine performs pre-flight file and video-readability checks. If a planned scene clip is missing or unreadable, assembly reports an error instead of producing the final output.

### 18. Can the system reconstruct the complete 3D property?
**Answer:** **No.** Full 3D geometric reconstruction (e.g. dense meshes, NeRF, 3D Gaussian Splatting) is explicitly out of scope. The system constructs a topological scene graph to guide generative video diffusion, preserving 2D photographic authenticity without fabricating 3D metric models.

### 19. How does the system handle panoramas and 360-degree viewing?
**Answer:** The system uses a multi-signal detection pipeline:
1. It inspects embedded XMP/GPano metadata tags (`GPano:ProjectionType="equirectangular"`).
2. It verifies the 2:1 geometric aspect ratio (width ≥ 1024px).
3. It analyzes boundary wrap-around seam continuity (comparing pixel variance between left column x=0 and right column x=W-1).
4. Genuine equirectangular panoramas render in an interactive 360° spherical Canvas viewer, while standard photos use bounded 2D pan/zoom without false spherical warping. Users can manually toggle any image's classification.

### 20. How are different photo aspect ratios handled in video assembly?
**Answer:** The current assembler targets 1280×720 at 24fps. Non-16:9 source content is scaled with proportional letterbox padding rather than intentional stretching; this does not remove artifacts introduced by the generative provider.

### 21. What future upgrades remain?
**Answer:**
1. Dependency on external cloud generative AI providers and active API credentials.
2. Generative diffusion models can occasionally introduce subtle texture shimmering or lighting drift.
3. Intermediate missing hallways are not hallucinated; rooms are connected via direct cuts or crossfades.
4. Output quality directly depends on the resolution, lighting, and coverage of the input photographs.

### 21. How is the generated output evaluated?
**Answer:** Through a dual evaluation system:
1. **Automated Verification Checks:** Probing scene analysis completeness, clip generation completeness, stream codec integrity, and plan synchronization.
2. **Human Evaluation Form:** A standardized 6-dimension rubric (Visual Quality, Consistency, Ordering, Motion, Stability, Usefulness) scored 1.0 to 5.0.

### 22. What is automated evaluation?
**Answer:** Objective, non-subjective technical checks executed by the server to verify that all elementary video streams are valid, uncorrupted, match target specifications (24fps, H.264), and reflect the current generation plan version.

### 23. What is human evaluation?
**Answer:** Structured quantitative feedback collected from users/reviewers across 6 core quality dimensions, paired with per-scene defect flags (`geometry_distortion`, `object_inconsistency`, `flickering`, `unnatural_motion`, `lighting_drift`).

### 24. Why did you use a provider-based image-to-video model instead of training your own?
**Answer:** State-of-the-art video diffusion models (like Gemini Veo) require billions of parameters, massive video pre-training datasets, and high-performance GPU clusters that exceed academic minor project compute constraints. Utilizing a foundation video model via SDK allows focusing on spatial reasoning, topological planning, camera trajectory synthesis, and end-to-end pipeline engineering.

### 25. What are the computational challenges?
**Answer:** Video diffusion inference is computationally intensive and latency-sensitive (30–60s per clip). The system addresses this with asynchronous job queues, progress tracking, per-scene caching, and independent clip concatenation.

### 26. What future improvements are possible?
**Answer:**
1. Integration of floor-plan diagram parsing (e.g. architectural blueprint inputs) to augment topological scene graphs with physical metric distances.
2. AI-driven ambient room acoustic generation matching detected room materials (e.g. echoing in large tiled living rooms vs damped sound in carpeted bedrooms).
3. Edge-optimized lightweight video diffusion models for local offline inference.
