from pydantic import BaseModel, HttpUrl
from typing import Optional, List
from datetime import datetime
from uuid import UUID

# --- Nested Schemas for consistency ---
# We can reuse the TagSummary from our main story schema if it's in a shared file.
class TagSummary(BaseModel):
    id: UUID
    name: str
    class Config:
        from_attributes = True

# --- Input Schemas (for creating/updating ads) ---

class AdCreate(BaseModel):
    advertiser_name: str
    ad_content: str
    destination_url: HttpUrl
    image_url: Optional[HttpUrl] = None
    tag_names: List[str] = [] # Use a list of names, not a single string
    weight: int = 1
    active: bool = True
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None

class AdUpdate(BaseModel):
    advertiser_name: Optional[str] = None
    ad_content: Optional[str] = None
    destination_url: Optional[HttpUrl] = None
    image_url: Optional[HttpUrl] = None
    tag_names: Optional[List[str]] = None
    weight: Optional[int] = None
    active: Optional[bool] = None
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None

# --- Output Schemas (for API responses) ---

# The full, detailed ad object for the admin panel
class AdOut(BaseModel):
    id: UUID
    advertiser_name: str
    ad_content: str
    destination_url: HttpUrl
    image_url: Optional[HttpUrl] = None
    weight: int
    active: bool
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    # A full ad object would also include its tags
    # tags: List[TagSummary] = [] 
    
    class Config:
        from_attributes = True

# A simplified object for serving the ad to the public
class AdServeOut(BaseModel):
    id: UUID
    advertiser_name: str
    ad_content: str
    image_url: Optional[HttpUrl] = None
    # The final, clickable URL, potentially with tracking params added by the service
    destination_url: HttpUrl 
    
    class Config:
        from_attributes = True

# For paginated lists in the admin panel
class AdList(BaseModel):
    items: List[AdOut]
