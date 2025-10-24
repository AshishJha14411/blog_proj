from pydantic import BaseModel
from typing import List, Optional
from app.schemas.stories import StoryOut # Import our unified StoryOut

class ToggleResponse(BaseModel):
    success: bool
    # Use Optional for fields that might not be present
    liked: Optional[bool] = None
    bookmarked: Optional[bool] = None

class BookmarkList(BaseModel):
    items: List[StoryOut]
