# Results and Reproducible Evaluation Template

This document defines what should be recorded when evaluating the current checkout. It does not claim that one fixed dataset, runtime, provider response, or human score applies to every run.

## 1. What is reproducible locally

Run the backend test suite from the backend directory:

```bash
./venv/bin/pytest tests/ -v
```

Run frontend checks from the frontend directory:

```bash
npm run lint
npm run build
```

The test count, execution time, generated media, and provider behavior can change as the code and dependencies change. Record the actual command output and date alongside any submitted result.

## 2. Suggested end-to-end record

For a demonstration dataset, record:

| Item | Value to record |
|---|---|
| Number of uploaded images | Actual count |
| Image formats and dimensions | Actual values |
| Number of analyzed scenes | Actual completed/total count |
| Number of generated clips | Actual completed/total count |
| Provider model | Configured `AI_MODEL` and `VIDEO_MODEL` |
| Quota pauses or retries | Actual job statuses and retry counts |
| Assembly output | Actual duration, resolution, frame rate, and file size |
| Evaluation scores | Reviewer name, rubric scores, and review date |

## 3. Output characteristics implemented by default

- Image uploads are limited by configuration; the default maximum is 20 images per project and 20 MB per image.
- Video generation requests are limited to 5 selected scenes by default.
- Remote Veo generation targets 4-second clips, one active submission at a time, with configurable pacing and retry settings.
- The assembler currently targets 1280×720 at 24fps and uses H.264 output when FFmpeg succeeds.
- The local slideshow fallback creates a non-generative MP4 and should be reported separately from Veo-generated output.

These are configuration defaults and implementation targets, not guarantees about provider latency or perceptual quality.

## 4. Human evaluation

Use the six rubric dimensions in [`evaluation.md`](evaluation.md). Report the number of reviewers, the input dataset, the score distribution, and the date. Do not present a single aggregate score as a general property of the system unless it was measured on a documented dataset.

## 5. Interpretation

The project demonstrates an end-to-end academic workflow: validated image ingestion, model-assisted scene analysis, deterministic ordering, optional Veo generation, local fallback generation, assembly, and review reporting. It is not evidence of production-scale throughput, guaranteed geometric fidelity, or unlimited free-tier availability.
