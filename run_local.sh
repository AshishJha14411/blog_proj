#!/usr/bin/env bash
#
# Bootstrap the whole stack (Postgres, backend, frontend) via docker-compose.
# Runs migrations + seed inside the backend container after it comes up so
# a fresh clone is one command away from a working dev environment.
#
# Prereqs: docker, docker compose plugin (v2), and a filled-out backend/.env
# (copy from backend/.env.example).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

# -------- 1. Fail fast on missing env --------

if [[ ! -f backend/.env ]]; then
  echo "ERROR: backend/.env is missing." >&2
  echo "       cp backend/.env.example backend/.env  and fill in real values." >&2
  exit 1
fi

if [[ ! -f .env ]]; then
  echo "WARN: repo-root .env not found — docker-compose will use empty \${VAR} defaults." >&2
  echo "      cp .env.example .env  and fill in real values for POSTGRES_*, ADMIN_*, etc." >&2
fi

# Required top-level compose variables. If any are unset we bail before Docker
# tries to build a container with silently-empty secrets.
set -a
[[ -f .env ]] && source .env
source backend/.env
set +a

REQUIRED=(SECRET_KEY JWT_SECRET_KEY ADMIN_USERNAME ADMIN_EMAIL ADMIN_PASSWORD)
missing=()
for name in "${REQUIRED[@]}"; do
  if [[ -z "${!name:-}" ]]; then
    missing+=("$name")
  fi
done
if (( ${#missing[@]} > 0 )); then
  echo "ERROR: required env vars are empty: ${missing[*]}" >&2
  echo "       Fill them in either .env or backend/.env before rerunning." >&2
  exit 1
fi

# -------- 2. Build + start containers --------

echo "==> docker compose up -d --build"
docker compose up -d --build

# -------- 3. Wait for backend /healthz --------

echo -n "==> waiting for backend /healthz "
for i in $(seq 1 60); do
  if curl -sf http://localhost:8000/healthz > /dev/null 2>&1; then
    echo " ok"
    break
  fi
  if (( i == 60 )); then
    echo
    echo "ERROR: backend never became ready within 120s." >&2
    echo "       docker compose logs backend" >&2
    exit 1
  fi
  echo -n "."
  sleep 2
done

# -------- 4. Migrations + seed --------
# Compose does bring the app up, but its entrypoint may skip the seed on
# reruns. Do it here explicitly so a fresh clone gets an admin user.

echo "==> alembic upgrade head"
docker compose exec -T backend alembic upgrade head

echo "==> python -m app.seed"
docker compose exec -T backend python -m app.seed || true  # idempotent seed

# -------- 5. Print URLs --------

cat <<EOF

Stack is up.
  Frontend  → http://localhost:3000
  Backend   → http://localhost:8000  (health: /healthz, docs: /docs)
  Postgres  → localhost:5432  (user=${POSTGRES_USER:-test_user}, db=${POSTGRES_DB:-test_db})

Tail logs with:
  docker compose logs -f backend frontend
Stop with:
  docker compose down
EOF
