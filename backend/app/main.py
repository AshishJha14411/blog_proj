from fastapi import FastAPI
from app.routes.auth import router as auth_router
from app.routes.posts import router as posts_router
from app.routes.comments import router as comments_router
from app.routes.interactions import router as interactions_router
from app.routes.moderation import router as moderation_router
from app.routes.tags import router as tags_router
from app.routes.analytics import router as analytics_router
from app.routes.admin import router as admin_router

app = FastAPI()

@app.get("/")
def read_root():
    return {"msg": "It works!"}

# from fastapi import FastAPI

app = FastAPI()
app.include_router(auth_router)
app.include_router(posts_router)
app.include_router(comments_router)
app.include_router(interactions_router)
app.include_router(moderation_router)
app.include_router(tags_router)
app.include_router(analytics_router)
app.include_router(admin_router)