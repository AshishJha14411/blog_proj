# app/services/media.py

from fastapi import HTTPException, status, UploadFile
from app.utils.cloudinary import upload_file

def upload_image(file: UploadFile, folder: str = "posts") -> str:
    """
    Uploads the incoming UploadFile to Cloudinary and returns the secure URL.
    """
    try:
        # `file.file` is a SpooledTemporaryFile, cloudinary accepts file-like
        url = upload_file(file.file, folder=folder)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Image upload failed"
        )
    return url
