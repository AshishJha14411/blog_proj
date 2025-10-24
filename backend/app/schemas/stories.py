from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional, Literal
from datetime import datetime
from uuid import UUID # Import UUID for type hinting if needed, though str is used for JSON

# --- Nested Schemas for Clean Responses ---

# A generic summary for nested user data
class UserSummary(BaseModel):
    id: UUID
    username: str
    class Config:
        from_attributes = True

# A generic summary for nested tag data
class TagSummary(BaseModel):
    id: UUID
    name: str
    class Config:
        from_attributes = True

# --- Input Schemas (Data coming IN to the API) ---

# Schema for a user MANUALLY creating a story
class StoryCreate(BaseModel):
    title: str
    header: Optional[str] = None
    content: str
    cover_image_url: Optional[HttpUrl] = None
    tag_names: List[str] = [] # Changed from `tags` for clarity
    is_published: bool = True

class StoryUpdate(BaseModel):
    title: Optional[str] = None
    header: Optional[str] = None
    content: Optional[str] = None
    cover_image_url: Optional[HttpUrl] = None
    tag_names: Optional[List[str]] = None # Changed from `tags`
    is_published: Optional[bool] = None

# --- AI Generation Input Schemas (Added Back) ---

class StoryGenerateIn(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None        # short description/blurb the user writes
    prompt: str                          # theme/instructions
    genre: Optional[str] = None
    tone: Optional[str] = None
    length_label: Optional[Literal["flash","short","medium","long"]] = None
    publish_now: bool = False
    temperature: Optional[float] = 0.8
    model_name: Optional[str] = "gpt-4o-mini"
    cover_image_url: Optional[HttpUrl] = None

class StoryFeedbackIn(BaseModel):
    feedback: str

# --- Output Schemas (Data going OUT from the API) ---

# This is our single, definitive schema for any story response.
class StoryOut(BaseModel):
    # Core Fields with correct types
    id: UUID # Correctly a string for UUID compatibility
    user_id: UUID # Correctly a string
    title: str
    content: str
    created_at: datetime
    updated_at: datetime
    
    # All optional fields from the old PostOut, now included
    header: Optional[str] = None
    cover_image_url: Optional[HttpUrl] = None
    is_published: bool
    source: Optional[str] = None
    
    # Nested related objects using our summary schemas
    user: UserSummary
    tags: List[TagSummary] = []
    
    # Extra computed fields for the frontend
    is_liked_by_user: bool = Field(False)
    is_bookmarked_by_user: bool = Field(False)
    

    class Config:
        from_attributes = True # Modern Pydantic V2 replacement for orm_mode

# Schema for paginated lists of stories
class StoryList(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[StoryOut] # Uses our new, unified StoryOut schema

    class Config:
        from_attributes = True

