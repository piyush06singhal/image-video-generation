# Vercel Deployment

## Recommended deployment topology

Deploy the Next.js frontend and FastAPI backend as two separate Vercel projects:

1. **Frontend project**
   - Import the repository in Vercel.
   - Set **Root Directory** to `frontend`.
   - Framework preset: **Next.js**.
   - Add `NEXT_PUBLIC_API_URL` with the deployed backend URL, for example:
     `https://your-backend.vercel.app`.

2. **Backend project**
   - Import the same repository as a second Vercel project.
   - Set **Root Directory** to `backend`.
   - The included [`vercel.json`](../backend/vercel.json) and [`api/index.py`](../backend/api/index.py) expose FastAPI.
   - Add the backend variables listed below.

## Backend environment variables

Set these in the backend Vercel project:

```env
GEMINI_API_KEY=your_key
VIDEO_API_KEY=your_key
VIDEO_MODEL=veo-3.1-generate-preview
CORS_ORIGINS=https://your-frontend.vercel.app
MAX_IMAGES_PER_PROJECT=20
MAX_ACTIVE_PROJECTS=10
MAX_SCENES_PER_GENERATION_REQUEST=5
MAX_CONCURRENT_GENERATIONS=1
VIDEO_SUBMISSION_INTERVAL_SECONDS=10
VIDEO_RATE_LIMIT_RETRY_ATTEMPTS=3
VIDEO_RATE_LIMIT_BACKOFF_SECONDS=15
```

Never commit these values or place them in frontend variables.

## Important backend constraint

The FastAPI adapter deploys on Vercel, but the current application is still a prototype
backend for video generation:

- Vercel filesystem writes are ephemeral and are not a durable project store.
- In-process `asyncio.create_task` jobs are not durable across serverless invocations.
- Long Veo polling, FFmpeg assembly, and slideshow rendering can exceed serverless limits.
- Multiple serverless instances do not share the local JSON project state.

Therefore, the Vercel backend is suitable for API experimentation and academic demos,
but it is **not** a reliable production video-generation worker. Before public use,
move project metadata and media to managed services, and move generation/assembly to a
durable worker or container service. The frontend can remain on Vercel.

## Verification

After deployment:

```bash
curl https://your-backend.vercel.app/api/health
```

Expected response:

```json
{"success":true,"data":{"status":"healthy","service":"walkthrough-backend"},"error":null}
```

Then open:

```text
https://your-frontend.vercel.app
https://your-frontend.vercel.app/studio
```
