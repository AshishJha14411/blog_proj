"""HTTP-shim entrypoint for running the Celery worker as a Cloud Run *service*.

WHY: a Cloud Run service requires its container to bind $PORT and pass a
startup probe. A Celery worker binds no port, so a naive deploy never becomes
ready. Here we run the worker in a background thread and serve a trivial
health endpoint in the foreground so the probe succeeds. Cloud Run Worker
Pools would remove the need for this shim, but that resource type isn't
available in this project (checked via `gcloud run worker-pools`), so this is
the portable fallback.

This is the container command ONLY for the dedicated worker service — the API
service keeps its default uvicorn CMD. The image's entrypoint.sh still runs
first; the worker service sets SKIP_MIGRATIONS=true so it doesn't race the API
on Alembic, then execs this module.
"""
from __future__ import annotations

import os
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer


def _start_worker() -> None:
    # `python -m celery` (not the bare `celery` console script) because deps
    # are installed via `pip install --target /app/deps` and aren't on PATH.
    # Concurrency/prefetch mirror docker-compose's worker service.
    subprocess.run(
        [
            "python", "-m", "celery",
            "-A", "app.worker.celery_app", "worker",
            "--loglevel=info",
            "--concurrency=2",
            "--prefetch-multiplier=1",
        ]
    )


class _Health(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 (http.server API)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *args) -> None:  # silence per-request access logs
        pass


def main() -> None:
    threading.Thread(target=_start_worker, daemon=True).start()
    port = int(os.environ.get("PORT", "8080"))
    HTTPServer(("0.0.0.0", port), _Health).serve_forever()


if __name__ == "__main__":
    main()
