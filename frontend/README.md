# CinéEstate Frontend

This is the Next.js 16 / React 19 client for the CinéEstate image-to-video walkthrough system.

## Getting Started

Configure `frontend/.env.local` (git-ignored, so a fresh clone does not have it):

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
# Must equal API_ACCESS_KEY in backend/.env, or every request is rejected with 401
NEXT_PUBLIC_API_KEY=
```

From the repository root, `python scripts/setup_env.py` creates this file **and** writes
the same shared key into it and into `backend/.env`, so the two sides cannot drift apart.

Install dependencies and run the development server:

```bash
npm install
npm run dev
```

`NEXT_PUBLIC_*` values are inlined at build time — changing them means restarting
`next dev`, not just the backend.

Open [http://localhost:3000](http://localhost:3000) for the landing page or [http://localhost:3000/studio](http://localhost:3000/studio) for the generation workflow.

The backend must be running at the configured API URL. See the repository [README](../README.md) for full-stack setup.

Useful checks:

```bash
npm run lint
npm run build
```

The Studio generation screen supports single-scene selection, quota-paused jobs, and a local image-slideshow fallback when Veo is unavailable.

## Vercel deployment

Deployed as its own Vercel project with `frontend/` as the **Root Directory**:

```bash
vercel login
bash scripts/deploy_vercel.sh     # deploys backend + frontend and connects them
```

or, manually, set:

```env
NEXT_PUBLIC_API_URL=https://your-backend.vercel.app
NEXT_PUBLIC_API_KEY=<same value as the backend's API_ACCESS_KEY>
```

and redeploy, because these are build-time values. The backend deployment adapter and its
serverless-runtime constraints are documented in
[`../docs/deployment-vercel.md`](../docs/deployment-vercel.md).
