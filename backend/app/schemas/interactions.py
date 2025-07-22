from pydantic import BaseModel
from typing import List
from app.schemas.posts import PostOut

class ToggleResponse(BaseModel):
    success: bool
    liked: bool = None
    bookmarked: bool = None

class BookmarkList(BaseModel):
    items: List[PostOut]
    class Config:
        from_attributes = True
