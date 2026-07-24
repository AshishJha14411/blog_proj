#!/bin/sh
set -e

# 1. Run the Master Setup Script (Migrations + Seeding) — once per stack
# startup. Other services sharing this image (e.g. the Celery worker) set
# SKIP_MIGRATIONS=true so they don't race the backend's migration/seed run
# against the same database.
if [ "${SKIP_MIGRATIONS:-false}" != "true" ]; then
  echo "Initializing application..."
  python -m app.seed
fi

# 2. Start the app — forwards whatever CMD/`command:` was given (uvicorn by
# default per the Dockerfile CMD, or the worker's celery command from
# docker-compose.yml) instead of hardcoding uvicorn for every service.
echo "Starting application..."
exec "$@"