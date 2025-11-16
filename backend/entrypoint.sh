#!/bin/sh

# This is a standard shell "shebang"
# 'set -e' means that the script will exit immediately if any command fails.
set -e

# 1. Run Alembic Migrations
# We tell alembic to find the 'alembic.ini' file and run all
# migrations up to the "head" (the latest version).
echo "Running database migrations..."
alembic upgrade head
# 2. Run the Data Seeding Script
echo "Running data seeding..."
python app/seed.py  # <-- ADD THIS LINE
# 2. Run the Command
# 'exec "$@"' is a shell command that means:
# "Replace this script with the command you were given"
# In our Dockerfile, this is the 'CMD ["uvicorn", "app.main:app", ...]'
echo "Starting application..."
exec "$@"