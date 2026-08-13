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

# --- Run as a non-root user (least privilege) ---
# A compromised web process shouldn't be root inside the container. Create an
# unprivileged user, hand it ownership of /app, and drop to it before running.
# The entrypoint only needs DB access + exec (no root-only writes, and
# PYTHONDONTWRITEBYTECODE avoids .pyc writes), so nothing here needs root.
RUN groupadd --system --gid 1001 appuser \
    && useradd --system --uid 1001 --gid appuser --home-dir /app appuser \
    && chown -R appuser:appuser /app
USER appuser

# Container-level liveness probe. Cloud Run uses its own probes and the Celery
# worker (same image, no HTTP port) disables this via compose, but locally this
# makes `docker ps` report real health for the API service. Uses stdlib only.
HEALTHCHECK --interval=30s --timeout=5s --start-period=25s --retries=3 \
    CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8080/healthz', timeout=3).status==200 else 1)"]

# Set the entrypoint
ENTRYPOINT ["/bin/sh","/app/entrypoint.sh"]

# Default command.
# --proxy-headers + --forwarded-allow-ips=* : Cloud Run terminates TLS and
# forwards to the container over plain HTTP with X-Forwarded-Proto: https.
# Without trusting that header, uvicorn thinks it's on http and builds
# redirect Location URLs as http:// — which an https frontend blocks as mixed
# content (e.g. the trailing-slash 307 on list endpoints). Trusting the
# forwarded proto makes redirects come back https. Safe on Cloud Run: only
# Google's front end can reach the container port.
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers", "--forwarded-allow-ips", "*"]