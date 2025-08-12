from fastapi import FastAPI
from app.routes.auth import router as auth_router
from app.routes.posts import router as posts_router
from app.routes.comments import router as comments_router
from app.routes.interactions import router as interactions_router
from app.routes.moderation import router as moderation_router
from app.routes.tags import router as tags_router
from app.routes.analytics import router as analytics_router
from app.routes.admin import router as admin_router
from app.routes.stories import router as stories_router
from app.routes.notifications import router as notifications_router


from fastapi.middleware.cors import CORSMiddleware
origins = [
    "http://localhost:3000",
    # "*"
]


app = FastAPI()

# Add the CORS middleware to your application.
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,      # Allow your frontend origin
    allow_credentials=True,   # Allow cookies to be included
    allow_methods=["*"],        # Allow all methods (GET, POST, etc.)
    allow_headers=["*"],        # Allow all headers
)


@app.get("/")
def read_root():
    return {"msg": "It works!"}

# from fastapi import FastAPI

# app = FastAPI()
app.include_router(auth_router)
app.include_router(posts_router)
app.include_router(comments_router)
app.include_router(interactions_router)
app.include_router(moderation_router)
app.include_router(tags_router)
app.include_router(analytics_router)
app.include_router(admin_router)
app.include_router(stories_router)
app.include_router(notifications_router)