# CinéEstate Frontend

This is the Next.js 16 / React 19 client for the CinéEstate image-to-video walkthrough system.

## Getting Started

Configure `frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Install dependencies and run the development server:

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) for the landing page or [http://localhost:3000/studio](http://localhost:3000/studio) for the generation workflow.

The backend must be running at the configured API URL. See the repository [README](../README.md) for full-stack setup.

Useful checks:

```bash
npm run lint
npm run build
```

The Studio generation screen supports single-scene selection, quota-paused jobs, and a local image-slideshow fallback when Veo is unavailable.

## Vercel deployment

Create a Vercel project with this directory as the **Root Directory** and set:

```env
NEXT_PUBLIC_API_URL=https://your-backend.vercel.app
```

The backend deployment adapter and its serverless-runtime constraints are documented in
[`../docs/deployment-vercel.md`](../docs/deployment-vercel.md).
