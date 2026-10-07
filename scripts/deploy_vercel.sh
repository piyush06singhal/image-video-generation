#!/usr/bin/env bash
# Deploy CinéEstate to Vercel: backend (FastAPI) + frontend (Next.js), connected.
#
# Prerequisites: `vercel login` has been run once (or VERCEL_TOKEN is set), and
# backend/.env holds the real provider keys.
#
# Phases: deploy backend -> push backend env -> point frontend at the backend ->
# deploy frontend -> widen backend CORS -> verify. Values are never printed.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ -n "${VERCEL_BIN:-}" ]; then
  BIN="$VERCEL_BIN"
elif command -v vercel >/dev/null 2>&1; then
  BIN="$(command -v vercel)"
elif [ -x "$ROOT/frontend/node_modules/.bin/vercel" ]; then
  BIN="$ROOT/frontend/node_modules/.bin/vercel"
elif [ -x /tmp/vercelcli/node_modules/.bin/vercel ]; then
  BIN=/tmp/vercelcli/node_modules/.bin/vercel
else
  echo "✗ Vercel CLI not found. Install it with: npm install -g vercel" >&2; exit 1
fi

TOKEN_ARGS=()
[ -n "${VERCEL_TOKEN:-}" ] && TOKEN_ARGS=(--token "$VERCEL_TOKEN")

BACKEND_PROJECT="${BACKEND_PROJECT:-cineestate-api}"
FRONTEND_PROJECT="${FRONTEND_PROJECT:-cineestate}"
TEAMS_ARGS=()
[ -n "${VERCEL_SCOPE:-}" ] && TEAMS_ARGS=(--scope "$VERCEL_SCOPE")

v() { "$BIN" "${TOKEN_ARGS[@]}" "${TEAMS_ARGS[@]}" "$@"; }

step() { printf '\n\033[1;34m== %s ==\033[0m\n' "$1"; }
die()  { echo "✗ $1" >&2; exit 1; }

# Fail fast with the fix, not three phases into a half-finished deployment.
if ! v whoami >/dev/null 2>&1; then
  die "Not authenticated with Vercel. Run \`vercel login\` once (it opens a browser), then re-run this script."
fi
echo "Authenticated as $(v whoami 2>/dev/null | tail -1)"

env_get() { # env_get FILE KEY -> value (empty if absent); never echoed
  python3 - "$1" "$2" <<'PY'
import sys
path, key = sys.argv[1], sys.argv[2]
try:
    for raw in open(path, encoding="utf-8"):
        line = raw.strip()
        if line.startswith(key + "="):
            print(line.split("=", 1)[1].strip().strip('"').strip("'"))
            break
except FileNotFoundError:
    pass
PY
}

set_env() { # set_env PROJECT KEY VALUE [envs...]
  local project="$1" key="$2" value="$3"; shift 3
  local envs="${*:-preview production}"
  [ -z "$value" ] && { echo "  · $key skipped (empty)"; return 0; }
  for e in $envs; do
    if v env ls "$key" --project "$project" 2>/dev/null | grep -q "^$key"; then
      v env rm "$key" "$e" --project "$project" --yes >/dev/null 2>&1 || true
    fi
    printf '%s' "$value" | v env add "$key" "$e" --project "$project" >/dev/null 2>&1 \
      && echo "  · $key -> $project ($e)" \
      || die "failed to set $key on $project"
  done
}

deploy() { # deploy DIR PROJECT -> URL
  local dir="$1" project="$2" out url
  step "Deploying $project from $dir/"
  v link --yes --project "$project" >/dev/null 2>&1 || true
  out="$( (cd "$ROOT/$dir" && v deploy --yes) 2>&1 )" || { echo "$out" | tail -30 >&2; die "deploy failed"; }
  url="$(echo "$out" | grep -Eo 'https://[A-Za-z0-9.-]+\.vercel\.app' | tail -1 || true)"
  [ -n "$url" ] || { echo "$out" | tail -40 >&2; die "could not read the deployment URL"; }
  echo "$url"
}

# ---------------------------------------------------------------------------
main() {
  [ -f "$ROOT/backend/.env" ] || die "backend/.env is missing — run: python scripts/setup_env.py"

  step "Phase 1/5 — backend"
  BACKEND_URL="$(deploy backend "$BACKEND_PROJECT")"
  echo "  ✓ $BACKEND_URL"

  step "Phase 2/5 — backend configuration (from backend/.env)"
  for key in API_ACCESS_KEY GEMINI_API_KEY AI_MODEL MAGIC_HOUR_API_KEY MAGIC_HOUR_MODEL \
             MAGIC_HOUR_RESOLUTION MAGIC_HOUR_AUDIO JSON2VIDEO_API_KEY JSON2VIDEO_RESOLUTION \
             VIDEO_PROVIDER VIDEO_FALLBACK_TO_LOCAL MAX_IMAGE_SIZE_BYTES MAX_IMAGE_PIXELS \
             MIN_IMAGE_WIDTH MIN_IMAGE_HEIGHT MAX_IMAGES_PER_PROJECT MAX_ACTIVE_PROJECTS \
             MAX_SCENES_PER_GENERATION_REQUEST MAX_CONCURRENT_GENERATIONS; do
    set_env "$BACKEND_PROJECT" "$key" "$(env_get "$ROOT/backend/.env" "$key")"
  done
  # The backend is now publicly reachable, so JSON2Video can finally fetch the
  # source photos it needs — the one thing a localhost deployment could not give it.
  set_env "$BACKEND_PROJECT" "PUBLIC_BASE_URL" "$BACKEND_URL"

  step "Phase 3/5 — frontend configuration"
  set_env "$FRONTEND_PROJECT" "NEXT_PUBLIC_API_URL" "$BACKEND_URL"
  set_env "$FRONTEND_PROJECT" "NEXT_PUBLIC_API_KEY" "$(env_get "$ROOT/backend/.env" "API_ACCESS_KEY")"

  step "Phase 4/5 — frontend"
  FRONTEND_URL="$(deploy frontend "$FRONTEND_PROJECT")"
  echo "  ✓ $FRONTEND_URL"

  step "Phase 5/5 — connect the two (CORS)"
  set_env "$BACKEND_PROJECT" "CORS_ORIGINS" \
    "$FRONTEND_URL,https://$FRONTEND_PROJECT.vercel.app,http://localhost:3000,http://127.0.0.1:3000"
  # CORS is read at process start, so the backend is redeployed to pick it up.
  (cd "$ROOT/backend" && v deploy --yes >/dev/null 2>&1) && echo "  ✓ backend redeployed with CORS_ORIGINS"

  step "Verify"
  if curl -sf -m 30 "$BACKEND_URL/api/health" >/dev/null 2>&1; then
    echo "  ✓ backend /api/health responded"
  else
    echo "  ⚠ backend /api/health did not respond yet (cold start can take ~20s)"
  fi

  echo
  echo "─────────────────────────────────────────────────────────────"
  echo "  Backend  : $BACKEND_URL"
  echo "  Frontend : $FRONTEND_URL"
  echo "─────────────────────────────────────────────────────────────"
  echo "  NEXT_PUBLIC_API_URL and NEXT_PUBLIC_API_KEY were set at build time, so any"
  echo "  future change to them needs a new frontend deployment."
}

main "$@"
