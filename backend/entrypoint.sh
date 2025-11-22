#!/bin/sh
set -e

# 1. Run the Master Setup Script (Migrations + Seeding)
echo "Initializing application..."
python -m app.seed

# 2. Start App
echo "Starting application..."
exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8080