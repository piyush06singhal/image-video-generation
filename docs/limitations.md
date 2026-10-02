# Academic Scope & System Boundaries

## 1. Architectural Scope & Boundary Decisions

This project is an **academic prototype** exploring generative vision-language planning and video diffusion for real estate walkthrough creation. It operates with the following explicit technical principles:

1. **Topological Graph vs. Metric 3D Reconstruction:**
   - The system constructs a directed topological graph representing room adjacency and sequence.
   - It explicitly does **not** perform Structure-from-Motion (SfM), Visual SLAM, dense Neural Radiance Fields (NeRF), or 3D Gaussian Splatting (3DGS).
   - This architectural decision enables rapid generative synthesis from sparse photographs (5–10 images) without requiring dense multi-view capture (100+ images) or high-end 3D scanning hardware.

2. **Zero Spatial Hallucination of Unseen Rooms:**
   - If photographs of an intermediate hallway, staircase, or corridor are omitted from the uploaded set, the system **never** hallucinates fictitious connecting architecture.
   - Rooms are connected using restrained direct cuts or brief 0.4s crossfades, preserving strict photographic authenticity.

3. **Multi-Signal Panorama Detection & Perspective Viewing:**
   - **Standard Perspective Photos:** Rendered via hardware-accelerated, bounded 2D pan/zoom without artificial spherical warping.
   - **Equirectangular 360° Panoramas:** Detected using a 3-tier validation hierarchy:
     1. Embedded XMP / GPano PhotoSphere metadata inspection (`GPano:ProjectionType="equirectangular"`).
     2. Strict 2:1 aspect ratio constraint (width ≥ 1024px).
     3. Left-right boundary edge wrap-around continuity analysis (calculating seam pixel correlation across 360° boundaries).
   - **User Override:** Users can toggle any image between 360° Spherical and 2D High-Res mode in Phase 2 and Phase 6.

4. **Proportional Geometric Preservation (Aspect Ratio Normalization):**
   - The final video output is standardized to high-definition 16:9 widescreen format (720p/1080p).
   - Non-16:9 source photographs (e.g. portrait 9:16 or square 1:1) are scaled with proportional geometric letterbox padding to prevent optical stretching, anamorphic distortion, or destructive cropping of room ceilings and floors.

---

## 2. Technical Dependencies & AI Constraints

1. **Generative Diffusion Model Behavior:**
   - Generative video models (e.g. Gemini Veo) may occasionally exhibit minor texture shimmering or boundary drift during camera motion.
   - The system mitigates this by injecting strict negative safety prompts (`no morphing, no warping architecture, no appearing people, static lighting`) and selecting conservative camera trajectories.

2. **Cloud AI Provider Requirement:**
   - Multimodal scene understanding and video diffusion synthesis require active Google GenAI credentials (`GEMINI_API_KEY`).
   - In the absence of API credentials, the system surfaces clear diagnostic errors rather than fabricating artificial videos.

3. **FFmpeg Environment:**
   - Video normalization and concatenation rely on FFmpeg, bundled automatically via `imageio-ffmpeg` or system binary.
