# Deploying: backend on Render, frontend on Vercel

This is the recommended topology for CinéEstate.

Vercel is an excellent host for the Next.js frontend and a poor one for this
backend. The backend renders video with FFmpeg for minutes at a time, keeps a
project tree on disk, scans it during startup, and holds in-process `asyncio`
generation jobs. A long-lived web service handles all three normally; a
serverless function formally cannot, because its filesystem is ephemeral, its
execution window is bounded, and its instances share no state.

Render gives the backend a real process, an optional persistent disk, and no
function timeout — while the frontend keeps Vercel's CDN, preview URLs and
build pipeline.

> The alternative, "everything on Vercel", is still documented in
> [`deployment-vercel.md`](deployment-vercel.md). It works for a demo and
> inherits the ephemeral-storage caveats.

---

## 1. Deploy the backend on Render

1. Sign in at [dashboard.render.com](https://dashboard.render.com).
2. **New → Blueprint**, then pick the `image-video-generation` repository.
   Render finds [`render.yaml`](../render.yaml) at the repository root and shows
   the service it will create.
3. Render prompts for the environment variables marked `sync: false`. Fill in:

   | Variable | Value |
   | :--- | :--- |
   | `API_ACCESS_KEY` | a shared secret — keep it, you need the same value on Vercel |
   | `GEMINI_API_KEY` | your Google AI Studio key |
   | `MAGIC_HOUR_API_KEY` | your Magic Hour key |
   | `JSON2VIDEO_API_KEY` | optional |
   | `PUBLIC_BASE_URL` | leave blank for now — set it after the first deploy |

4. **Apply**. The first build installs `backend/requirements.txt` and starts
   `uvicorn` behind Render's proxy. Expect a few minutes: OpenCV and the bundled
   FFmpeg binary are large.
5. Copy the service URL — `https://cineestate-api.onrender.com`.
6. Set `PUBLIC_BASE_URL` to that URL and let it redeploy. This is what lets
   JSON2Video download source photos; it is impossible from localhost.

### Verify before touching the frontend

```bash
curl -s https://cineestate-api.onrender.com/api/health | python3 -m json.tool
```

Expect `"status": "healthy"`, `"is_serverless": false`, and a `video_provider`
of `magic_hour` rather than `kenburns` — `kenburns` means your key did not load.
The response also reports `env_files` and which providers are configured, so a
misconfiguration is visible without guessing.

---

## 2. Point the frontend at it

In the **Vercel** frontend project, under **Settings → Environment Variables**:

| Name | Value |
| :--- | :--- |
| `NEXT_PUBLIC_API_URL` | `https://cineestate-api.onrender.com` |
| `NEXT_PUBLIC_API_KEY` | the **same** value as `API_ACCESS_KEY` |

Then **redeploy** the frontend. `NEXT_PUBLIC_*` values are inlined at build
time, so changing them without a rebuild does nothing.

The Render blueprint already sets `CORS_ORIGIN_REGEX` to admit every
`*.vercel.app` origin, which is necessary because **Vercel assigns a new
hostname to every preview deployment** — a static allow-list would break on each
branch build. Add any custom domain to `CORS_ORIGINS` as well.

---

## Persistent storage

**Render free instances cannot attach a persistent disk.** Without one the
service filesystem is ephemeral: projects are lost on every deploy, restart, or
15-minute idle spin-down. That is fine for evaluating the pipeline in one
sitting and not fine for anything else.

To keep data:

1. Upgrade the service to a paid instance type (a persistent disk requires one).
2. Add a disk mounted at `/var/data` — in the dashboard, or by uncommenting the
   `disk:` block in [`render.yaml`](../render.yaml).
3. Uncomment `STORAGE_DIR` and set it to `/var/data/storage`.

`STORAGE_DIR` must be absolute, and it must sit under the disk's mount path —
only files below that path survive a restart. The application resolves a
*relative* `STORAGE_DIR` against the `backend` package, which lands on the
ephemeral filesystem and would silently lose projects.

---

## Free-tier expectations

| Behaviour | Detail |
| :--- | :--- |
| RAM / CPU | 512 MB, 0.1 CPU. Enough for the API, AI scene analysis and remote generation. Local Ken Burns rendering and 1080p assembly are memory-hungry — upgrade to `1c-2g` before relying on them. |
| Idle spin-down | After ~15 minutes of inactivity the instance stops; the next request takes about a minute to wake it. `/api/health` is the cheapest way to warm it before a demo. |
| Deploys | Every push to the linked branch triggers a rebuild, which also discards the ephemeral filesystem. |
| Bandwidth | Free tier bandwidth is limited; serving large MP4s burns it quickly. |

---

## Troubleshooting

| Symptom | Cause | Fix |
| :--- | :--- | :--- |
| Frontend says the backend is unreachable | Render instance asleep | Load `/api/health` once to wake it, then retry |
| Every request returns 401 | `API_ACCESS_KEY` and `NEXT_PUBLIC_API_KEY` differ | Set both to the same value and redeploy the frontend |
| Browser console shows a CORS error | Origin not allowed | Confirm `CORS_ORIGIN_REGEX` is set, or add the exact origin to `CORS_ORIGINS` |
| Clips come back from the local renderer | No provider key loaded, or credits exhausted | Check the `configured` block in `/api/health` |
| Projects vanish after a while | No persistent disk; the filesystem is ephemeral | Attach a disk and set `STORAGE_DIR` |
| Build fails on a dependency | Stale build cache | **Manual Deploy → Clear build cache & deploy** |

Run the project's own diagnostic against the deployment:

```bash
python scripts/check_config.py --url https://cineestate-api.onrender.com
```

It reports key fingerprints (never values), which environment files the backend
loaded, and whether the frontend and backend halves agree about the shared key.
