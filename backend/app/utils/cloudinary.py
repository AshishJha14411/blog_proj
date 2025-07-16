import cloudinary
import cloudinary.uploader
from app.core.config import settings

# initialize once
cloudinary.config( 
    cloud_name = settings.CLOUDINARY_CLOUD_NAME,
    api_key    = settings.CLOUDINARY_API_KEY,
    api_secret = settings.CLOUDINARY_API_SECRET,
    secure     = True
)

def upload_file(file, folder: str = "") -> str:
    """
    Accepts a file-like or path, uploads to Cloudinary,
    returns the secure URL.
    """
    result = cloudinary.uploader.upload(
        file,
        folder=folder,
        overwrite=True
    )
    return result.get("secure_url")
