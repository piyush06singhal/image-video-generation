# CinéEstate

Turn an unordered set of real-estate photographs into a cinematic video walkthrough.

[![Backend](https://img.shields.io/badge/backend-FastAPI-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![Frontend](https://img.shields.io/badge/frontend-Next.js%2016%20%C2%B7%20React%2019-000000?style=flat-square&logo=next.js)](https://nextjs.org)
[![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?style=flat-square&logo=python)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-blue?style=flat-square)](LICENSE)

---

## Overview

A photo gallery asks a buyer to reconstruct a property in their head. CinéEstate produces
the tour instead, without 3D scanning hardware — no Matterport rig, no multi-view capture,
just the photographs an agent already has.

The design constraint that shapes everything: **the pipeline is deterministic and the
property must never be hallucinated**. Scene ordering, camera moves, transitions, grading
and the score are computed from the photographs and a persisted plan. Only the optional
generative engines synthesise new pixels, and they are opt-in.

Each stage persists its output as JSON beside the media, so the pipeline is resumable and
any later stage can be recomputed without re-running the earlier ones.

---

## Architecture

### Pipeline stages

| # | Stage | What happens |
| :--- | :--- | :--- |
| 1 | **Ingest** | Validates and EXIF-normalises each upload, de-duplicates by SHA-256, and classifies equirectangular panoramas from multiple signals. The 20 MB byte limit is enforced *while streaming* and a 40 MP canvas limit is checked *before decoding*. |
| 2 | **Understand** | Gemini vision assigns each photograph a room type, lighting assessment, architectural features and a quality score. |
| 3 | **Plan** | Builds a directed scene graph and orders it by architectural hierarchy — exterior → entrance → social → private → outdoor — then chooses a conservative camera move and transition per room. Only uploaded rooms are planned. |
| 4 | **Render** | Produces one short moving shot per room through the configured engine. Every engine implements one interface and receives the same camera instruction and grounding constraints, so the plan and assembly are engine-independent. |
| 5 | **Assemble** | Cover-crops each clip to the target frame so no black bars ever ship, applies the selected grade, composites title and lower-third cards, mixes a composed score, and lands a synthesised sting on every cut. |
| 6 | **Inspect** | Spherical viewer for 360° panoramas, bounded 2D pan/zoom for perspective photos, automated verification, and a human evaluation rubric. |

### Render engines

| `VIDEO_PROVIDER` | Motion source | Cost | Property accuracy |
| :--- | :--- | :--- | :--- |
| `kenburns` | Local camera move over the real photo (OpenCV + FFmpeg) | Free, offline, no quota | Exact — the pixels are the listing |
| `json2video` | Cloud render of the real photos (pan/zoom + transitions) | Free tier ≈ 600 s of render; needs a public URL | Exact — the pixels are the listing |
| `magic_hour` | Generative diffusion over one still (Kling / LTX / Veo / Seedance) | Credits per second of output; no public URL needed | Can invent furniture and geometry |
| `gemini_veo` | Generative diffusion (Veo) | Hardest free tier | Can invent furniture and geometry |
| `auto` *(default)* | Best configured remote engine, local fallback | — | Degrades instead of failing |

In `auto`, a rate limit, exhausted quota, content block or misconfiguration degrades the
affected clip to the local renderer rather than failing the walkthrough, so a tour is always
produced. Set `VIDEO_PROVIDER=kenburns` for a fully offline run with zero API calls.

---

## Getting started

### Prerequisites

- Python 3.10 or newer
- Node.js 18 or newer
- No system FFmpeg required: it ships inside the `imageio-ffmpeg` wheel

### 1. Configure

```bash
python scripts/setup_env.py
```

Run this once per clone. Real keys live in `backend/.env` and `frontend/.env.local`, both
git-ignored, so a fresh checkout starts with no configuration at all. The script creates
both files and writes **one shared key** into `API_ACCESS_KEY` and `NEXT_PUBLIC_API_KEY` so
the two halves cannot disagree. Then edit `backend/.env` and add your provider keys.

### 2. Start the backend

```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

API base `http://localhost:8000` · interactive docs `/docs` · health `/api/health`

Optional: `backend/models/depth_anything_v2_small.onnx` (~100 MB, not committed) adds 2.5D
depth parallax to the local renderer. Without it the renderer falls back to a flat camera
move; nothing else changes.

### 3. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Studio `http://localhost:3000/studio` · landing page `http://localhost:3000`

### 4. Verify your setup

```bash
python scripts/check_config.py                                     # local files
python scripts/check_config.py --url https://your-backend.example  # probe a deployment
```

Both print key *fingerprints* (8 hex characters of a SHA-256) and never values, so the
output is safe to paste into a bug report.

### Troubleshooting

| Symptom | Cause | Fix |
| :--- | :--- | :--- |
| Every request returns 401 | `API_ACCESS_KEY` and `NEXT_PUBLIC_API_KEY` differ, or one is unset | Run `python scripts/setup_env.py`, then restart `next dev` |
| The backend has no keys | `backend/.env` was never created — it is git-ignored | Run `python scripts/setup_env.py` |
| Stage 2 fails while the rest works | `GEMINI_API_KEY` is missing or still a placeholder | Add the key and restart |
| Clips come from the local renderer | No video engine key, or credits exhausted | Expected degradation; add a provider key for generative motion |
| A new `NEXT_PUBLIC_*` value has no effect | It is inlined at **build** time | Restart `next dev`; on Vercel, redeploy |

The backend resolves `.env` relative to its own package, so it loads the same keys whatever
directory it is started from.

---

## Configuration

Everything is environment-driven. The templates are the authoritative reference:
[`backend/.env.example`](backend/.env.example) and
[`frontend/.env.example`](frontend/.env.example). The settings that matter most:

| Variable | Purpose |
| :--- | :--- |
| `GEMINI_API_KEY` | Required. Vision model used for scene understanding. |
| `VIDEO_PROVIDER` | One of `auto`, `json2video`, `magic_hour`, `gemini_veo`, `kenburns`. |
| `MAGIC_HOUR_API_KEY` | Generative motion, no public URL required. |
| `JSON2VIDEO_API_KEY` + `PUBLIC_BASE_URL` | Cloud render over the real photographs. |
| `API_ACCESS_KEY` | Shared secret guarding `/api`; must equal `NEXT_PUBLIC_API_KEY`. |
| `MAX_IMAGE_SIZE_BYTES` / `MAX_IMAGE_PIXELS` | Upload byte cap and decompression-bomb cap. |
| `CORS_ORIGINS` / `CORS_ORIGIN_REGEX` | Allowed browser origins. The regex covers preview URLs, which change on every deployment. |

### Render options

A per-project `render_options.json` controls the look: frame shape and quality, pacing,
camera variety, transitions, titles, colour grade and score. Both the render and assembly
stages read it, so regenerating reproduces the same style. Five presets ship built in, each
a complete option set so one can be applied atomically and then tweaked coherently:

| Preset | Grade | Motion and pace | Transition | Score |
| :--- | :--- | :--- | :--- | :--- |
| `cinematic_luxury` | Warm luxury, vignette, grain, bloom | Balanced · 4.5 s · 30 fps | Crossfade 0.6 s | Ambient |
| `modern_minimal` | Cool modern, no vignette or grain | Subtle · 4.0 s · 30 fps | Crossfade 0.5 s | Minimal piano |
| `energetic_reel` | Cinematic teal, vignette, grain, bloom | Bold · 3.0 s · **9:16** | Slide left 0.4 s | Uplifting |
| `documentary_tour` | Natural, no grade | Subtle · 6.0 s · 24 fps | Crossfade 0.5 s | Off |
| `quick_draft` | Natural, no grade | Subtle · 3.0 s, effects off | Straight cut 0.3 s | Off |

Room labels are on for every preset except `quick_draft`, the room counter is off for
`documentary_tour` and `quick_draft`, and `quick_draft` also disables depth parallax and
motion blur so a preview renders in a fraction of the time.

Changing a look-only option flags the assembled video as outdated rather than silently
leaving a stale file in place.

---

## Testing

```bash
cd backend && ./venv/bin/pytest -q
cd frontend && npx tsc --noEmit && npm run build
```

The suite covers all six stages plus the provider integrations, the API-key guard, upload
limits and configuration resolution. `API_ACCESS_KEY` is neutralised by default so a local
key cannot turn every API test into a 401; the guard has its own opt-in tests.

---

## Deployment

### Recommended: backend on Render, frontend on Vercel

The backend renders video with FFmpeg for minutes at a time, keeps a project tree on disk
and scans it at startup, and holds in-process generation jobs. A long-lived web service does
all three; a serverless function formally cannot.

1. **Backend → Render.** New → Blueprint → pick this repository.
   [`render.yaml`](render.yaml) defines the service and Render prompts for the secrets.
2. **Frontend → Vercel.** Set `NEXT_PUBLIC_API_URL` to the Render URL and
   `NEXT_PUBLIC_API_KEY` to the same value as `API_ACCESS_KEY`, then redeploy.
3. **Set `PUBLIC_BASE_URL`** on the Render service to its own URL. This is what lets the
   JSON2Video renderer download source photographs, which localhost never could.

CORS needs no manual step: the blueprint sets `CORS_ORIGIN_REGEX` for `*.vercel.app`, which
matters because Vercel assigns a new hostname to every preview deployment.

Full walkthrough: [`docs/deployment-render.md`](docs/deployment-render.md).

### Alternative: both applications on Vercel

```bash
vercel login
bash scripts/deploy_vercel.sh     # deploys both and wires them together
```

See [`docs/deployment-vercel.md`](docs/deployment-vercel.md) for the serverless constraints
that come with it.

---

## Project structure

```
├── backend/
│   ├── app/
│   │   ├── api/v1/          # all REST routes (health and projects)
│   │   ├── core/            # settings, error types, logging
│   │   ├── schemas/         # Pydantic models for every stage
│   │   └── services/
│   │       ├── image_preprocessor.py   # validation, EXIF, panorama detection
│   │       ├── scene_analyzer/         # Gemini vision engine
│   │       ├── walkthrough_planner/    # scene graph, camera and transition planning
│   │       ├── video_generation/       # provider interface and four engines
│   │       └── video_assembler/        # FFmpeg engine, grade, cards, score
│   ├── api/index.py         # serverless entrypoint (optional topology)
│   └── tests/               # pytest suite
├── frontend/
│   ├── app/                 # landing page and /studio
│   ├── components/          # studio UI, one component per stage
│   ├── lib/api.ts           # typed API client
│   └── types/               # interfaces mirroring the Pydantic schemas
├── docs/                    # technical reference and evaluation material
├── scripts/                 # setup, diagnostics and deployment
└── render.yaml              # Render blueprint
```

---

## Documentation

| Document | Contents |
| :--- | :--- |
| [architecture.md](docs/architecture.md) | Module responsibilities, data flow, storage layout and configuration resolution |
| [api.md](docs/api.md) | Every REST endpoint, its payloads, and the authentication contract |
| [deployment-render.md](docs/deployment-render.md) | Recommended deployment, persistent storage and troubleshooting |
| [deployment-vercel.md](docs/deployment-vercel.md) | All-Vercel alternative and its serverless constraints |
| [evaluation.md](docs/evaluation.md) | Metric formulas, verification rules and rubric scoring |
| [results.md](docs/results.md) | Reproducible test commands and a result-recording template |
| [viva.md](docs/viva.md) | Technical defence questions with grounded answers |
| [final-demo.md](docs/final-demo.md) | End-to-end demonstration script |
| [presentation-outline.md](docs/presentation-outline.md) | Slide structure with talking points |
| [screenshots.md](docs/screenshots.md) | Screenshot capture checklist |
| [future-upgrades.md](docs/future-upgrades.md) | Boundaries, explicit non-goals and planned work |

---

## Scope and limitations

The system is deliberately explicit about what it is not:

| Boundary | Detail |
| :--- | :--- |
| **Not 3D reconstruction** | A topological scene graph, not dense SfM, NeRF or Gaussian splatting. There is no metric geometry, and output quality depends on how many photographs you supply and how well they cover the property. |
| **No invented rooms** | Only uploaded scenes are planned and rendered. The pipeline does not fabricate clips for spaces nobody photographed. |
| **Generative engines drift** | `magic_hour` and `gemini_veo` synthesise pixels and can invent furniture, warp geometry or change finishes. `kenburns` and `json2video` move a camera over the real photograph and are pixel-exact by construction. Accuracy versus spectacle is a trade-off the operator selects, not one the system hides. |
| **Cover-crop, not letterbox** | The video pipeline fills the requested frame so no black bars ship, which centre-crops landscape photographs into a `9:16` reel. The viewer keeps full source geometry. |
| **Procedural score** | The soundtrack is composed locally from oscillators and filters. No licensed recording, no downloaded assets. |

---

## License

MIT — see [LICENSE](LICENSE).
