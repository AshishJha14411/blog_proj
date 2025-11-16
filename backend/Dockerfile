# --- STAGE 1: The "Builder" Stage ---
# We start with a full Python image to build our dependencies
FROM python:3.12-slim as builder

# 1. Set up the environment
WORKDIR /app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=off

# 2. Install the system dependencies required to *build* Python packages
# (e.g., psycopg2-binary needs libpq-dev)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 3. Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip
# This builds all packages and installs them into a temporary venv
RUN pip install -r requirements.txt --target /app/deps


# --- STAGE 2: The "Final" Stage ---
# We start from a fresh, *tiny* Python image for the final product
FROM python:3.12-slim

WORKDIR /app

# Set environment variables again
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
# Tell Python where to find the packages we installed
ENV PYTHONPATH=/app/deps

# 1. Install *only* the runtime system dependencies
# (e.g., psycopg2-binary needs libpq5, but not the -dev compiler)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# 2. Copy the pre-built dependencies from the "builder" stage
COPY --from=builder /app/deps ./deps

# 3. Copy our application code
# We copy alembic, the .ini, and the 'app' folder
COPY ./alembic ./alembic
COPY alembic.ini .
COPY ./app ./app

# 4. We will create an 'entrypoint' script to run migrations
COPY ./entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# 5. Set the entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]

# 6. Set the default command to run
# This is what the entrypoint script will run *after* migrations
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]