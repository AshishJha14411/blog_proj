# app/routes/media.py
from fastapi import APIRouter, Depends, File, UploadFile, status
from app.services.media import upload_image
from app.dependencies import get_current_user

router = APIRouter(prefix="/media", tags=["Media"])

@router.post("/upload", status_code=status.HTTP_201_CREATED)
def media_upload(file: UploadFile = File(...), current_user = Depends(get_current_user)):
    url = upload_image(file, folder=f"users/{current_user.id}")
    return {"url": url}
