# CinéEstate

**Turn an unordered set of real-estate photographs into a cinematic video walkthrough.**

CinéEstate is an end-to-end pipeline and inspection studio: it validates and de-duplicates
uploaded photographs, understands them with a vision language model, orders them into a
plausible tour, renders each room as a short moving shot, and assembles the result into a
graded, scored walkthrough — with a viewer for inspecting 360° panoramas and a rubric for
evaluating the output.

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
property must never be hallucinated.** Scene ordering, camera moves, transitions, grading
and the score are all computed from the photographs and a persisted plan. Only the optional
generative providers synthesise new pixels, and they are opt-in.

---

## How it works

```
photographs
    │
    ▼
1  Ingest      validate · EXIF-normalise · SHA-256 de-duplicate · panorama detection
    │
    ▼
2  Understand  Gemini vision → room type, lighting, features, quality score
    │
    ▼
3  Plan        topological scene graph → tour order → per-room camera + transition
    │
    ▼
4  Render      one 4-second shot per room, via the configured provider
    │
    ▼
5  Assemble    conform · brand cards · labels · grade · score · sting every cut
    │
    ▼
6  Inspect     spherical panorama viewer · 2D pan/zoom · verification · evaluation
```

Each stage persists its output as JSON beside the media, so the pipeline is resumable and
every later stage can be recomputed without re-running the earlier ones.

**Ingestion** enforces a 20 MB byte limit *while streaming the upload* and a 40 MP canvas
limit *before decoding*, de-duplicates by content hash, and detects equirectangular
panoramas from multiple signals rather than a single aspect-ratio guess.

**Planning** builds a directed scene graph and orders it by architectural hierarchy
(exterior → entrance → social → private → outdoor). It plans only the rooms you uploaded —
it does not invent intermediate spaces to smooth the tour.

**Rendering** is provider-agnostic. Every engine implements one interface and receives the
same camera instruction and grounding constraints, so the plan, prompts and assembly are
independent of which engine produced the pixels.

**Assembly** cover-crops each clip to the target frame (so no black bars ever ship), applies
the selected grade, composits title and lower-third cards, mixes a procedurally composed
score, and lands a synthesised sting on every cut using the assembly's own cut positions.

### Render engines

| `VIDEO_PROVIDER` | Motion source | Cost | Property accuracy |
| :--- | :--- | :--- | :--- |
| `kenburns` | Local camera move over the real photo (OpenCV + FFmpeg) | Free, offline, no quota | Exact — pixels are the listing |
| `json2video` | Cloud render of the real photos (pan/zoom + transitions) | Free tier ≈ 600 s of render; needs a public URL | Exact — pixels are the listing |
| `magic_hour` | Generative diffusion over one still (Kling / LTX / Veo / Seedance) | Credits per second of output; no public URL needed | Can invent furniture and geometry |
| `gemini_veo` | Generative diffusion (Veo) | Hardest free tier | Can invent furniture and geometry |
| `auto` *(default)* | Best configured remote, local fallback | — | Degrades instead of failing |

In `auto`, a rate limit, exhausted quota, content block or misconfiguration degrades the
affected clip to the local renderer rather than failing the walkthrough — so a tour is
always produced. Set `VIDEO_PROVIDER=kenburns` for a fully offline run with zero API calls.

---

## Quick start

**Prerequisites:** Python ≥ 3.10, Node.js ≥ 18. FFmpeg ships inside the `imageio-ffmpeg`
wheel, so nothing needs installing system-wide.

### 1. Configure

```bash
python scripts/setup_env.py
```

Run this once per clone. Real keys live in `backend/.env` and `frontend/.env.local`, both
git-ignored, so a fresh checkout starts with no configuration at all. This script creates
both files and writes **one shared key** into `API_ACCESS_KEY` and `NEXT_PUBLIC_API_KEY`,
so the two halves can never disagree. Then edit `backend/.env` and add your provider keys.

### 2. Backend

```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

* API base `http://localhost:8000` · interactive docs `/docs` · health `/api/health`

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

* Studio `http://localhost:3000/studio` · landing page `http://localhost:3000`

Optional: `backend/models/depth_anything_v2_small.onnx` (~100 MB, not committed) adds 2.5D
depth parallax to the local renderer. Without it the renderer falls back to a flat camera
move — nothing else changes.

### Verify your configuration

```bash
python scripts/check_config.py                                     # local files
python scripts/check_config.py --url https://your-backend.example  # probe a deployment
```

Both print key *fingerprints* (8 hex characters of a SHA-256), never values, so the output
is safe to paste into a bug report.

### If keys work on one machine but not another

| Symptom | Cause | Fix |
| :--- | :--- | :--- |
| Every request returns 401 | `API_ACCESS_KEY` and `NEXT_PUBLIC_API_KEY` differ, or one is unset | `python scripts/setup_env.py`, then restart `next dev` |
| Backend has no keys | `backend/.env` was never created (it is git-ignored) | `python scripts/setup_env.py` |
| Phase 2 fails, the rest works | `GEMINI_API_KEY` missing or still a placeholder | Add the key and restart |
| Clips come from the local renderer | No video provider key, or credits exhausted | Expected degradation |
| A new `NEXT_PUBLIC_*` value has no effect | It is inlined at **build** time | Restart `next dev`; on Vercel, redeploy |

The backend resolves `.env` relative to its own package, so it loads the same keys whatever
directory it is started from.

---

## Testing

```bash
cd backend && ./venv/bin/pytest -q        # 230+ tests
cd frontend && npx tsc --noEmit && npm run build
```

The suite covers all six phases plus the provider integrations, the API-key guard, upload
limits and configuration resolution. `API_ACCESS_KEY` is neutralised by default so a local
key cannot turn every API test into a 401; the guard has its own opt-in tests.

---

## Configuration

Everything is environment-driven; the templates are the reference:
[`backend/.env.example`](backend/.env.example) and
[`frontend/.env.example`](frontend/.env.example). The settings that matter most:

| Variable | Purpose |
| :--- | :--- |
| `GEMINI_API_KEY` | Required. Vision model for scene understanding. |
| `VIDEO_PROVIDER` | `auto` \| `json2video` \| `magic_hour` \| `gemini_veo` \| `kenburns` |
| `MAGIC_HOUR_API_KEY` | Generative motion with no public URL required. |
| `JSON2VIDEO_API_KEY` + `PUBLIC_BASE_URL` | Cloud render over the real photos. |
| `API_ACCESS_KEY` | Shared secret guarding `/api`; must equal `NEXT_PUBLIC_API_KEY`. |
| `MAX_IMAGE_SIZE_BYTES` / `MAX_IMAGE_PIXELS` | Upload byte cap and decompression-bomb cap. |
| `CORS_ORIGINS` / `CORS_ORIGIN_REGEX` | Allowed browser origins; the regex covers preview URLs that change per deployment. |

A per-project `render_options.json` controls the look — frame shape and quality, pacing,
camera variety, transitions, titles, colour grade, and score — with five presets
(`cinematic_luxury`, `modern_minimal`, `energetic_reel`, `documentary_tour`, `quick_draft`).
Both the render and assembly stages read it, so a regenerate reproduces the same style.
Changing a look-only option flags the assembled video as outdated rather than silently
leaving a stale file in place.

---

## Deployment

**Recommended: backend on Render, frontend on Vercel.**

```bash
# Backend → Render:  New → Blueprint → pick this repository
#                    (render.yaml defines the service; Render prompts for secrets)
```

Then set `NEXT_PUBLIC_API_URL` (the Render URL) and `NEXT_PUBLIC_API_KEY` (the same value
as `API_ACCESS_KEY`) on the Vercel frontend project and redeploy. Finally set
`PUBLIC_BASE_URL` on the Render service to its own URL — that is what lets the JSON2Video
renderer download source photos, which localhost never could.

This split is deliberate. The backend renders video with FFmpeg for minutes at a time,
keeps a project tree on disk and scans it at startup, and holds in-process generation jobs.
A long-lived web service does all three; a serverless function formally cannot.

* Walkthrough: [`docs/deployment-render.md`](docs/deployment-render.md)
* Alternative, both apps on Vercel: [`docs/deployment-vercel.md`](docs/deployment-vercel.md)

---

## Repository layout

```
├── backend/
│   ├── app/
│   │   ├── api/v1/          # all REST routes (health + projects)
│   │   ├── core/            # settings, error types, logging
│   │   ├── schemas/         # Pydantic models for every phase
│   │   └── services/
│   │       ├── image_preprocessor.py      # validation, EXIF, panorama detection
│   │       ├── scene_analyzer/            # Gemini vision provider
│   │       ├── walkthrough_planner/       # scene graph, camera + transition planning
│   │       ├── video_generation/          # provider interface + 4 engines
│   │       └── video_assembler/           # FFmpeg engine, grade, cards, score
│   ├── api/index.py         # serverless entrypoint (optional topology)
│   └── tests/               # pytest suite
├── frontend/
│   ├── app/                 # landing page + /studio
│   ├── components/          # studio UI per phase
│   ├── lib/api.ts           # typed API client
│   └── types/               # interfaces mirroring the Pydantic schemas
├── docs/                    # technical reference and evaluation material
├── scripts/                 # setup, diagnostics, deployment
└── render.yaml              # Render blueprint
```

---

## Documentation

| Document | Contents |
| :--- | :--- |
| [architecture.md](docs/architecture.md) | Module responsibilities, data flow, storage layout, configuration resolution |
| [api.md](docs/api.md) | Every REST endpoint, payloads, and the authentication contract |
| [deployment-render.md](docs/deployment-render.md) | Recommended deployment, persistent storage, troubleshooting |
| [deployment-vercel.md](docs/deployment-vercel.md) | All-Vercel alternative and its serverless constraints |
| [evaluation.md](docs/evaluation.md) | Metric formulas, verification rules, rubric scoring |
| [results.md](docs/results.md) | Reproducible test commands and result-recording template |
| [viva.md](docs/viva.md) | Technical defence questions with grounded answers |
| [final-demo.md](docs/final-demo.md) | End-to-end demonstration script |
| [presentation-outline.md](docs/presentation-outline.md) | Slide structure with talking points |
| [screenshots.md](docs/screenshots.md) | Screenshot capture checklist |
| [future-upgrades.md](docs/future-upgrades.md) | Boundaries, explicit non-goals, and planned work |

---

## Scope and limitations

The system is honest about what it is and is not:

- **Not 3D reconstruction.** It builds a topological scene graph, not dense SfM, NeRF or
  Gaussian splatting. There is no metric geometry, and output quality depends on how many
  photographs you supply and how well they cover the property.
- **No invented rooms.** Only uploaded scenes are planned and rendered; the pipeline does
  not fabricate clips for spaces nobody photographed.
- **Generative providers drift.** `magic_hour` and `gemini_veo` synthesise pixels and can
  invent furniture, warp geometry or change finishes. The plate-based engines (`kenburns`,
  `json2video`) move a camera over the real photograph and are pixel-exact by construction.
  Accuracy versus spectacle is a trade-off the operator selects, not one the system hides.
- **Cover-crop, not letterbox.** The video pipeline fills the requested frame so no black
  bars ever ship, which centre-crops landscape photos into a `9:16` reel. The viewer keeps
  full source geometry.
- **Procedural score.** The soundtrack is composed locally from oscillators and filters —
  no licensed recording, no downloaded assets.

---

## License

MIT — see [LICENSE](LICENSE).
