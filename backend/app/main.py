from fastapi import FastAPI
from app.routes.auth import router as auth_router
from app.routes.posts import router as post_router


app = FastAPI()
@app.get("/")
def read_root():
    return {"msg": "It works!"}


app.include_router(auth_router)
app.include_router(post_router)