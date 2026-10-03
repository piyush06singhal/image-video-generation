# Academic Scope & System Boundaries

## 1. Architectural Scope & Boundary Decisions

This project is an **academic prototype** exploring generative vision-language planning and video diffusion for real estate walkthrough creation. It operates with the following explicit technical principles:

1. **Topological Graph vs. Metric 3D Reconstruction:**
   - The system constructs a directed topological graph representing room adjacency and sequence.
   - It explicitly does **not** perform Structure-from-Motion (SfM), Visual SLAM, dense Neural Radiance Fields (NeRF), or 3D Gaussian Splatting (3DGS).
   - This avoids metric reconstruction and specialist scanning hardware, but output quality still depends on the number, coverage, and quality of uploaded photographs.

2. **Conservative handling of unseen rooms:**
   - If an intermediate hallway, staircase, or corridor is not uploaded, the planner does not add a separate scene for it.
   - Rooms are connected using the configured transition. Generative motion inside an uploaded scene can still contain provider-specific artifacts.

3. **Multi-Signal Panorama Detection & Perspective Viewing:**
   - **Standard Perspective Photos:** Rendered via hardware-accelerated, bounded 2D pan/zoom without artificial spherical warping.
   - **Equirectangular 360° Panoramas:** Detected using heuristic signals:
     1. Embedded XMP / GPano PhotoSphere metadata inspection (`GPano:ProjectionType="equirectangular"`).
     2. Strict 2:1 aspect ratio constraint (width ≥ 1024px).
     3. When needed, left-right boundary edge continuity analysis.
   - Detection is a classifier signal, not proof that every image is a valid panorama.
   - **User Override:** Users can toggle any image between 360° Spherical and 2D High-Res mode in Phase 2 and Phase 6.

4. **Proportional Geometric Preservation (Aspect Ratio Normalization):**
   - The current assembler targets 1280×720 (16:9) at 24fps.
   - Non-16:9 source photographs (e.g. portrait 9:16 or square 1:1) are scaled with proportional geometric letterbox padding to prevent optical stretching, anamorphic distortion, or destructive cropping of room ceilings and floors.

---

## 2. Technical Dependencies & AI Constraints

1. **Generative Diffusion Model Behavior:**
   - Generative video models (e.g. Gemini Veo) may occasionally exhibit minor texture shimmering or boundary drift during camera motion.
   - The system mitigates this with direct prompt constraints that preserve furniture, walls, geometry, and lighting, plus conservative camera trajectories. The current Veo 3.1 integration does not send a separate negative-prompt field.

2. **Cloud AI Provider Requirement:**
   - Multimodal scene understanding and video diffusion synthesis require active Google GenAI credentials (`GEMINI_API_KEY`, or the configured `VIDEO_API_KEY` for video generation).
   - In the absence of API credentials, the system surfaces clear diagnostic errors rather than fabricating artificial videos.

3. **FFmpeg Environment:**
   - Video normalization and concatenation rely on FFmpeg, bundled automatically via `imageio-ffmpeg` or system binary.

## 3. Future Upgrades & Release Priorities

1. **Provider quotas are not removed by application code:**
   - Free-tier Gemini/Veo projects have provider-controlled request and daily quotas.
   - The application now defaults to one Veo generation at a time, spaces submissions, and retries transient rate-limit responses with exponential backoff.
   - Reliable multi-user production generation still requires paid quota, per-tenant quotas, and a durable worker queue.

2. **The current queue is process-local:**
   - Background generation jobs are stored in project JSON, but active asyncio tasks live only in the running API process.
   - A process restart does not resume an in-flight provider operation automatically.
   - This is acceptable for the prototype; Redis/Celery or a managed task queue should be added before production deployment.

3. **Local storage and credentials are prototype boundaries:**
   - Uploaded images and generated videos are stored on the backend filesystem.
   - There is no user authentication, tenant isolation, object-storage lifecycle policy, or per-user billing/quota enforcement.
   - These are higher priority than additional visual polish when onboarding real users.

4. **Generation latency is expected:**
   - Veo generation is asynchronous and can take minutes per scene.
   - The UI should treat generation as a queued workflow rather than an immediate request/response operation.

5. **Prototype safety limits are configurable:**
   - A local installation defaults to 20 images per project, 10 active projects, and 5 scenes per generation request.
   - These limits protect a free-tier/demo deployment from accidental bursts; they are not a substitute for authentication or tenant-level quotas.
