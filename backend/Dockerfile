# --- STAGE 1: The "Builder" Stage ---
# FIX 1: Force the correct architecture for Cloud Run (amd64)
FROM --platform=linux/amd64 python:3.12-slim as builder

WORKDIR /app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=off

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt --target /app/deps


# --- STAGE 2: The "Final" Stage ---
# FIX 1: Force the correct architecture here too
FROM --platform=linux/amd64 python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app/deps

# FIX 2: Install 'dos2unix' to fix Windows line endings
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libpq5 \
    dos2unix \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/deps ./deps

COPY ./alembic ./alembic
COPY alembic.ini .
COPY ./app ./app

# Copy the entrypoint
COPY ./entrypoint.sh /app/entrypoint.sh

# FIX 2: Run dos2unix on the script to remove invisible Windows characters
RUN dos2unix /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# Set the entrypoint
ENTRYPOINT ["/bin/sh","/app/entrypoint.sh"]

# Default command
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]