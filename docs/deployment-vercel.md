# Deploying CinéEstate to Vercel

> **This is the alternative topology.** The recommended setup puts the backend on a
> long-lived host and keeps only the frontend on Vercel, because video rendering,
> a persistent project tree and in-process generation jobs do not fit serverless
> functions. See [`deployment-render.md`](deployment-render.md) first; the
> [Serverless reality check](#serverless-reality-check) below explains the trade-off.

Both apps deploy to Vercel as **two separate projects** — the Next.js frontend and the
FastAPI backend — with the frontend pointed at the backend by a build-time environment
variable.

## The fast path

```bash
vercel login                    # once; credentials live outside the repository
bash scripts/deploy_vercel.sh   # deploys both apps and wires them together
```

The script, in order:

| Phase | Action |
| :--- | :--- |
| 1 | Deploy `backend/` as project `cineestate-api`, capture the deployment URL |
| 2 | Push the backend configuration from `backend/.env` (values are transferred, never printed) |
| 3 | Set `PUBLIC_BASE_URL` to the deployed backend URL |
| 4 | Set `NEXT_PUBLIC_API_URL` / `NEXT_PUBLIC_API_KEY` on the frontend project, then deploy `frontend/` as project `cineestate` |
| 5 | Set `CORS_ORIGINS` to the frontend origin and redeploy the backend |
| 6 | Probe `/api/health` and print both URLs |

`PUBLIC_BASE_URL` is worth calling out: JSON2Video downloads every source photo over
HTTP, so it needs a publicly reachable origin. **This is the one capability a Vercel
backend unlocks that localhost never could** — no tunnel required.

Overridable variables (see the top of the script): `BACKEND_PROJECT`, `FRONTEND_PROJECT`,
`VERCEL_SCOPE`, `VERCEL_TOKEN`, `VERCEL_BIN`.

## Manual deployment

1. **Backend** — import the repository, set **Root Directory** to `backend`.
   - `backend/vercel.json` routes every request to `api/index.py`, the FastAPI entrypoint.
   - `backend/.python-version` pins Python 3.12.
   - `backend/.vercelignore` and the `excludeFiles` glob keep tests, the ~100 MB depth
     model and local storage out of the bundle.
2. **Frontend** — import the repository again, set **Root Directory** to `frontend`,
   framework preset **Next.js**.
3. Add the environment variables below, then redeploy.

## Environment variables

### Backend (`cineestate-api`)

```env
GEMINI_API_KEY=<your key>
MAGIC_HOUR_API_KEY=<your key>
JSON2VIDEO_API_KEY=<your key>
PUBLIC_BASE_URL=https://cineestate-api.vercel.app   # set after the first deploy
CORS_ORIGINS=https://cineestate.vercel.app,http://localhost:3000
API_ACCESS_KEY=<shared secret, must equal the frontend's NEXT_PUBLIC_API_KEY>
MAX_IMAGE_SIZE_BYTES=20971520
MAX_IMAGE_PIXELS=40000000
MAX_IMAGES_PER_PROJECT=20
MAX_ACTIVE_PROJECTS=10
MAX_SCENES_PER_GENERATION_REQUEST=5
MAX_CONCURRENT_GENERATIONS=1
VIDEO_PROVIDER=auto
VIDEO_FALLBACK_TO_LOCAL=true
```

`scripts/deploy_vercel.sh` sets all of these from `backend/.env` automatically. Never put
provider keys in the *frontend* project: `NEXT_PUBLIC_*` values are inlined into the
public JavaScript bundle and are visible to anyone who opens DevTools.

### Frontend (`cineestate`)

```env
NEXT_PUBLIC_API_URL=https://cineestate-api.vercel.app
NEXT_PUBLIC_API_KEY=<must equal the backend's API_ACCESS_KEY>
```

Because `NEXT_PUBLIC_*` is inlined at **build** time, changing either value requires a new
frontend deployment — restarting or redeploying the backend does nothing.

## Serverless reality check

Read this before pointing the tool at real users. Vercel functions are ephemeral:

- **The filesystem is read-only except `/tmp`, and `/tmp` does not survive between
  invocations.** The app detects this at startup (`VERCEL` in the environment) and
  redirects storage to `/tmp/storage`, and `/api/health` reports
  `"is_serverless": true`. A project uploaded in request A is *not* guaranteed to be
  visible in request B.
- **In-process background jobs are not durable.** Generation runs through
  `asyncio.create_task` inside one function instance; a new instance cannot see it, and a
  scale-in or timeout loses it.
- **Long renders do not fit the time budget.** `maxDuration` is set to 60 s. A Magic Hour
  clip takes minutes to render remotely and an FFmpeg assembly is CPU-bound and slower
  still, so assembly and the local slideshow renderer are the first things to be cut off.
- **Instances do not share state**, so two concurrent requests can disagree about what
  exists.

### What works well

Project creation, image upload and validation, AI scene analysis, plan generation and
editing, render-option management, Magic Hour clip generation (the photo is uploaded to
Magic Hour, so no public URL is needed), and the inspection/evaluation workflow — for a
single user testing in one session.

### What needs more infrastructure

Durable, shared media storage (an object store), a long-running worker for generation and
assembly, and a database for project metadata. See
[`docs/future-upgrades.md`](future-upgrades.md).

## Verification

```bash
# Backend is up and reports its configuration
curl -s https://cineestate-api.vercel.app/api/health | python3 -m json.tool

# Or with the project's own diagnostic
python scripts/check_config.py --url https://cineestate-api.vercel.app
```

A healthy response reports `status: healthy`, the resolved `video_provider`, the
environment files that were loaded, and `auth_required` — which must be `true` whenever
`API_ACCESS_KEY` is set, and must be matched by the frontend's `NEXT_PUBLIC_API_KEY`.

Then open:

```text
https://cineestate.vercel.app/studio
```

If the studio loads but every action fails with 401, the two halves disagree about the
shared key — the banner in the studio says so explicitly, and
`python scripts/setup_env.py` fixes it.
