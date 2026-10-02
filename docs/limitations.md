# Academic Scope & System Limitations

## 1. Explicit Architectural Non-Goals

This project is an **academic prototype** exploring generative vision-language planning and video diffusion for real estate walkthrough creation. It explicitly operates within the following boundaries:

1. **No Full 3D Geometric Reconstruction:**
   - The system does **not** perform Structure from Motion (SfM), Visual SLAM, dense Neural Radiance Fields (NeRF), or 3D Gaussian Splatting (3DGS).
   - The spatial graph represents *topological connectivity* and *architectural ordering*, not metrically precise 3D floor plan meshes.

2. **No Hallucinated Intermediate Hallways:**
   - If photographs for an intermediate corridor, hallway, or staircase are not supplied, the system does not invent or hallucinate synthetic connecting rooms.
   - Transitions between adjacent rooms are rendered using restrained direct cuts or short crossfades (0.4s).

3. **Immersive Viewer Boundary Conditions:**
   - For **standard perspective photographs**, the immersive viewer provides high-resolution 2D pan/zoom. It does not wrap planar photographs onto false 3D spheres.
   - For **equirectangular 360° panoramas**, the 2:1 aspect ratio serves as a detection signal, not absolute proof. The user has an override toggle to correct classification.

---

## 2. Technical Limitations & External Dependencies

1. **Diffusion Model Hallucinations:**
   - Generative video models (e.g. Gemini Veo) may occasionally exhibit minor texture shimmering, subtle object drift, or edge blurring during camera motion.
   - Restrained negative prompts and camera trajectory constraints are enforced to minimize these artifacts.

2. **AI Provider Availability & Credentials:**
   - Multimodal scene understanding and video diffusion synthesis require active Google GenAI credentials (`GEMINI_API_KEY`).
   - If API credentials are not configured, the system provides clear diagnostic warnings rather than creating fake video files.

3. **Single Aspect Ratio Alignment:**
   - Generated scene video clips and final assembled walkthrough videos are normalized to 16:9 widescreen format (720p/1080p). Non-16:9 source photographs are scaled with uniform letterboxing to prevent optical stretching or distortion.

4. **FFmpeg Environment Requirement:**
   - Video normalization and concatenation rely on FFmpeg binary availability (provided automatically via `imageio-ffmpeg` or system PATH).
