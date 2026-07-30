# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from app.core.config import settings
# Routers
from app.routes.auth import router as auth_router
from app.routes.story import router as posts_router
from app.routes.comments import router as comments_router
from app.routes.interactions import router as interactions_router
from app.routes.moderation import router as moderation_router, user_action_router
from app.routes.tags import router as tags_router
from app.routes.analytics import router as analytics_router
from app.routes.admin import router as  admin_features_router
from app.routes.notifications import router as notifications_router
from app.routes.ads import router as ad_admin_router, public_router as ad_public_router
from app.routes.webhooks import router as webhooks_router
from app.ws.routes import router as ws_router
from app.support.routes import router as support_ws_router
# Logging utils & middleware
from app.middleware.logging import LoggingMiddleware
from app.middleware.idempotency import IdempotencyMiddleware
from app.observability import setup_logging, init_sentry, instrument_metrics
from app.error_handlers import register_exception_handlers
from app.routes import media

# ---- Observability: structured logging (+ Sentry in prod) ----
setup_logging()
init_sentry()
app_logger = logging.getLogger("app")

app = FastAPI()

# Prometheus /metrics (no-op if the instrumentator isn't installed).
instrument_metrics(app)

# Middleware stack — add order is INNERMOST first (the last added wraps the
# rest). Target request flow: CORS -> Logging -> Idempotency -> route, so a
# replayed idempotent response still gets logged + an x-request-id.
app.add_middleware(IdempotencyMiddleware)          # innermost
app.add_middleware(LoggingMiddleware)              # request-id + timing

frontend_url = settings.FRONTEND_URL.rstrip("/") if settings.FRONTEND_URL else ""

# Define allowed origins
origins = [
    "http://localhost:3000",  # Always allow local dev
]

# Only add the production frontend URL if it's set
if frontend_url:
    origins.append(frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # <-- Use the dynamic list
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# RFC 7807 problem+json handlers (HTTPException, validation, catch-all 500).
register_exception_handlers(app)

@app.get("/")
def read_root():
    return {"msg": "It works!"}


@app.get("/healthz")
def healthz():
    """Liveness probe for CI / docker-compose healthchecks."""
    return {"status": "ok"}

# Routers
# All HTTP/JSON routers live under a single versioned prefix so the API surface
# can evolve behind /api/v2 later without breaking /api/v1 clients. Each router
# keeps its own sub-prefix (/stories, /auth, …), so this just prepends the
# version. Infra endpoints (/, /healthz, /metrics) and the WebSocket routers
# stay at the top level on purpose — probes and the WS handshake aren't part of
# the versioned REST contract.
API_V1_PREFIX = "/api/v1"

_HTTP_ROUTERS = [
    auth_router, posts_router, comments_router, interactions_router,
    moderation_router, tags_router, analytics_router, admin_features_router,
    notifications_router, ad_admin_router, ad_public_router, webhooks_router,
    media.router, user_action_router,
]

# Canonical, documented surface: everything under /api/v1.
for _r in _HTTP_ROUTERS:
    app.include_router(_r, prefix=API_V1_PREFIX)

# ---------------------------------------------------------------------------
# LEGACY UNVERSIONED MOUNT — deprecation window, remove after the frontend ships
# ---------------------------------------------------------------------------
# /** WHY: introducing /api/v1 is a breaking change to the API contract, and the
#     deployed frontend still calls the unversioned paths. A hard cutover would
#     require deploying backend + frontend in the same instant; mounting both
#     lets them ship independently — which is how a real version migration is
#     done (serve N and N-1 for a window, then retire N-1). **/
# /** WHY-THIS-WAY: `include_in_schema=False` keeps the legacy copies out of
#     /openapi.json, so the docs advertise only /api/v1 and the frontend's
#     generated types can't accidentally pin to the deprecated paths. **/
# /** REMOVE WHEN: the Vercel frontend is deployed on /api/v1 and access logs
#     show no unversioned traffic. Tracked in docs/DEPLOY.md. **/
for _r in _HTTP_ROUTERS:
    app.include_router(_r, include_in_schema=False)

# WebSocket routers stay top-level (not part of the versioned REST contract).
app.include_router(ws_router)
app.include_router(support_ws_router)