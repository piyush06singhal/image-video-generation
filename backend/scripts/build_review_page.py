#!/usr/bin/env python
"""Generates a static review page comparing rendered walkthroughs with their sources.

Usage:
    ./venv/bin/python scripts/build_review_page.py [project_id ...]

With no arguments it reviews every project that has a final walkthrough, newest
first. The page is written to ``storage/projects/_review/index.html`` and loads
media straight from the running backend (the ``/file`` routes are unauthenticated
by design so ``<img>``/``<video>`` work), so start the API first:

    ./venv/bin/python -m uvicorn app.main:app --port 8000
"""

import html
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings  # noqa: E402

REVIEW_DIR = settings.STORAGE_DIR / "projects" / "_review"
BACKEND = "http://127.0.0.1:8000"


def _projects_with_final_video(explicit: list[str]) -> list[Path]:
    root = settings.STORAGE_DIR / "projects"
    if explicit:
        return [root / pid for pid in explicit if (root / pid).is_dir()]
    found = [
        d
        for d in root.iterdir()
        if d.is_dir() and not d.name.startswith("_") and (d / "final" / "walkthrough.mp4").exists()
    ]
    return sorted(found, key=lambda d: (d / "final" / "walkthrough.mp4").stat().st_mtime, reverse=True)


def _source_photo(project: Path, image_id: str) -> Path | None:
    matches = sorted((project / "uploads").glob(f"{image_id}*"))
    return matches[0] if matches else None


def _scene_rows(project: Path) -> str:
    """One row per scene: source photograph beside the clip rendered from it."""
    meta_path = project / "final" / "metadata.json"
    if not meta_path.exists():
        return "<p class='muted'>No assembly metadata.</p>"
    meta = json.loads(meta_path.read_text())
    pid = project.name

    rows = []
    for scene in meta.get("scenes_in_order", []):
        photo = _source_photo(project, scene["image_id"])
        photo_tag = (
            f"<img src='{BACKEND}/api/projects/{pid}/images/{scene['image_id']}/file' alt='source'>"
            if photo
            else "<div class='missing'>source photo missing</div>"
        )
        rows.append(
            f"""
        <div class="scene">
          <div class="scene-head">
            <span class="order">{scene['order']:02d}</span>
            <span class="label">{html.escape(scene['label'])}</span>
            <span class="muted">{scene['scene_type'].replace('_', ' ')} · {scene['duration_seconds']:.1f}s</span>
          </div>
          <div class="pair">
            <figure><figcaption>Source photo</figcaption>{photo_tag}</figure>
            <figure>
              <figcaption>Rendered clip — {html.escape(scene.get('transition_to_next', '').replace('_', ' '))}</figcaption>
              <video controls preload="metadata"
                     src="{BACKEND}/api/projects/{pid}/clips/{scene['scene_id']}/file"></video>
            </figure>
          </div>
        </div>"""
        )
    return "\n".join(rows)


def _project_section(project: Path) -> str:
    pid = project.name
    final = project / "final" / "walkthrough.mp4"
    if not final.exists():
        return ""
    meta = json.loads((project / "final" / "metadata.json").read_text())
    proj = json.loads((project / "project.json").read_text()) if (project / "project.json").exists() else {}
    options = meta.get("render_options") or {}
    clips_meta = json.loads((project / "generation.json").read_text()) if (project / "generation.json").exists() else {}
    engines = sorted({c.get("provider", "?") for c in clips_meta.get("clips", [])})

    chips = [
        f"{meta['width']}×{meta['height']}",
        f"{meta['fps']:.0f} fps",
        f"{meta['duration_seconds']:.1f}s",
        f"{meta['scene_count']} scenes",
        f"{(meta['file_size_bytes'] / 1e6):.1f} MB",
        f"audio: {meta.get('audio_codec') or 'none'}",
        f"engine: {', '.join(engines) or 'unknown'}",
        f"modified: {__import__('datetime').datetime.fromtimestamp(final.stat().st_mtime).strftime('%Y-%m-%d %H:%M')}",
    ]
    if options:
        chips += [
            f"preset: {options.get('preset')}",
            f"grade: {options.get('color_grade')}",
            f"transition: {options.get('transition_style')}",
            f"motion: {options.get('motion_intensity')}",
            f"music: {options.get('music_style') if options.get('music_enabled') else 'silent'}",
            f"labels: {'on' if options.get('room_labels_enabled') else 'off'}",
            f"cards: intro={'on' if options.get('intro_title_enabled') else 'off'} / outro={'on' if options.get('outro_enabled') else 'off'}",
            # Production-value features: the ones that decide whether a render
            # reads as a produced film or as a photo slideshow.
            f"depth: {'2.5D parallax' if options.get('depth_parallax') else 'flat camera'}",
            f"blur: {'on' if options.get('motion_blur') else 'off'}",
            f"bloom: {'on' if options.get('cinematic_bloom') else 'off'}",
            f"bars: {'on' if options.get('letterbox') else 'off'}",
        ]
        if options.get("brand_text"):
            chips.append(f"brand: {options['brand_text']}")

    outdated = "<span class='warn'>STALE — settings changed since this render</span>" if meta.get("is_outdated") else ""

    return f"""
    <section class="project">
      <header>
        <div>
          <h2>{html.escape(proj.get('name') or pid)}</h2>
          <p class="muted mono">{pid} {outdated}</p>
        </div>
      </header>
      <div class="chips">{''.join(f'<span class="chip">{html.escape(str(c))}</span>' for c in chips)}</div>
      <video class="final" controls preload="metadata"
             src="{BACKEND}/api/projects/{pid}/final-video/file"></video>
      <div class="actions">
        <a class="btn" href="{BACKEND}/api/projects/{pid}/final-video/file" target="_blank">Open MP4 in a new tab</a>
        <a class="btn ghost" href="{BACKEND}/api/projects/{pid}/final-video/download">Download</a>
      </div>
      <h3>Scene-by-scene: source photo vs generated clip</h3>
      {_scene_rows(project)}
    </section>"""


def main() -> int:
    projects = _projects_with_final_video(sys.argv[1:])
    if not projects:
        print("No projects with a final walkthrough found. Render one first.")
        return 1

    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    out = REVIEW_DIR / "index.html"
    out.write_text(
        f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>CinéEstate — rendered walkthrough review</title>
<style>
  :root {{ color-scheme: dark; }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; padding:32px 20px 80px; background:#0b0c0e; color:#e9edf2;
         font:14px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; }}
  .wrap {{ max-width:1080px; margin:0 auto; }}
  h1 {{ font-size:26px; margin:0 0 6px; letter-spacing:-.02em; }}
  h2 {{ font-size:19px; margin:0; }}
  h3 {{ font-size:12px; text-transform:uppercase; letter-spacing:.09em; color:#8e9aa8;
        margin:26px 0 12px; font-weight:700; }}
  .muted {{ color:#8e9aa8; font-size:12px; }}
  .mono {{ font-family:ui-monospace,SFMono-Regular,Menlo,monospace; }}
  .warn {{ color:#ffce5c; font-weight:700; }}
  .project {{ margin:34px 0; padding:22px; border:1px solid #23262b; border-radius:18px;
              background:linear-gradient(180deg,#121417,#0e1013); }}
  .chips {{ display:flex; flex-wrap:wrap; gap:7px; margin:14px 0 16px; }}
  .chip {{ background:#1b1f24; border:1px solid #2a2f36; color:#cbd4de; padding:3px 9px;
           border-radius:999px; font-size:11px; font-family:ui-monospace,Menlo,monospace; }}
  .final {{ width:100%; border-radius:14px; background:#000; border:1px solid #23262b; display:block; }}
  .actions {{ display:flex; gap:9px; margin-top:12px; flex-wrap:wrap; }}
  .btn {{ background:#d4a853; color:#17120a; text-decoration:none; font-weight:700; font-size:12px;
          padding:8px 14px; border-radius:10px; }}
  .btn.ghost {{ background:transparent; color:#d4a853; border:1px solid #3a3f47; }}
  .scene {{ border-top:1px solid #1e2227; padding:16px 0; }}
  .scene-head {{ display:flex; align-items:center; gap:11px; margin-bottom:11px; }}
  .order {{ background:#d4a85322; color:#e0b768; border:1px solid #4a3f22; border-radius:8px;
            padding:2px 8px; font-weight:700; font-size:12px; font-family:ui-monospace,monospace; }}
  .pair {{ display:grid; grid-template-columns:1fr 1fr; gap:13px; }}
  @media (max-width:720px) {{ .pair {{ grid-template-columns:1fr; }} }}
  figure {{ margin:0; }}
  figcaption {{ font-size:11px; color:#8e9aa8; margin-bottom:5px; }}
  figure img, figure video {{ width:100%; border-radius:11px; border:1px solid #23262b;
                              background:#000; display:block; object-fit:cover; }}
  .missing {{ border:1px dashed #444; border-radius:11px; padding:28px; text-align:center;
              color:#777; font-size:12px; }}
</style>
</head>
<body>
<div class="wrap">
  <h1>Rendered walkthrough review</h1>
  <p class="muted">{len(projects)} project(s) with a final video, newest render first.
     Media is streamed live from the API at {BACKEND}.</p>
  {''.join(_project_section(p) for p in projects)}
</div>
</body>
</html>""",
        encoding="utf-8",
    )
    print(f"Wrote {out} covering {len(projects)} project(s):")
    for p in projects:
        print(f"  - {p.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
