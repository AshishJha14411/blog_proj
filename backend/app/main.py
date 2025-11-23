# app/main.py
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
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
# Logging utils & middleware
from app.utils.db_logger import DatabaseLogHandler, PiiScrubbingFilter
from app.middleware.logging import LoggingMiddleware
from app.routes import media
# ---- App-scoped logger (avoid root) ----
app_logger = logging.getLogger("app")
app_logger.setLevel(logging.INFO)
app_logger.propagate = False

db_handler = DatabaseLogHandler(level=logging.ERROR)  # persist only ERROR+
db_handler.addFilter(PiiScrubbingFilter())
app_logger.addHandler(db_handler)

stderr_handler = logging.StreamHandler()
stderr_handler.setLevel(logging.INFO)
app_logger.addHandler(stderr_handler)

# Keep noisy libraries out of DB handler
logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
logging.getLogger("uvicorn").setLevel(logging.INFO)
logging.getLogger("uvicorn.error").setLevel(logging.INFO)
logging.getLogger("uvicorn.access").setLevel(logging.INFO)

# Optionally strip handlers from root to avoid double logs
for h in list(logging.getLogger().handlers):
    logging.getLogger().removeHandler(h)

app = FastAPI()

# Make middleware log to "app" logger (ensure your middleware accepts logger_name or uses "app" internally)
app.add_middleware(LoggingMiddleware)  # if middleware uses logging.getLogger("app")

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

# Global exception handler -> "app" logger
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    app_logger.exception(
        "Unhandled 500 Internal Server Error",
        extra={
            "request_context": {
                "method": request.method,
                "url": str(request.url),
                "headers": dict(request.headers),  # scrubbed by PiiScrubbingFilter
                "client_ip": request.client.host if request.client else "unknown",
                "request_id": getattr(request.state, "request_id", "N/A"),
            }
        },
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred. The team has been notified."},
    )

@app.get("/")
def read_root():
    return {"msg": "It works!"}

# Routers
app.include_router(auth_router)
app.include_router(posts_router)
app.include_router(comments_router)
app.include_router(interactions_router)
app.include_router(moderation_router)
app.include_router(tags_router)
app.include_router(analytics_router)
app.include_router(admin_features_router)
app.include_router(notifications_router)
app.include_router(ad_admin_router)
app.include_router(ad_public_router)
app.include_router(media.router)
app.include_router(user_action_router) 