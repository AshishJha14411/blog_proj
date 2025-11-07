from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional, Literal
from datetime import datetime
from uuid import UUID # Import UUID for type hinting if needed, though str is used for JSON

# --- Nested Schemas for Clean Responses ---
class AuthorPreview(BaseModel):
    id: UUID
    username: str

    model_config = dict(from_attributes=True)

class TagOut(BaseModel):
    id: UUID
    name: str

    model_config = dict(from_attributes=True)
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

class StoryOut(BaseModel):
    id: UUID
    title: str
    content: str

    # DB fields
    user_id: UUID
    is_published: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_liked_by_user: bool = False
    is_bookmarked_by_user: bool = False
    # Relations / projections (often optional in responses)
    author: Optional[AuthorPreview] = None
    tags: List[TagOut] = Field(default_factory=list)
    header: Optional[str] = None
    cover_image_url: Optional[str] = None
    source: str = "user"  
    # Computed / analytics fields (default to zero/False)
    likes_count: int = 0
    bookmarks_count: int = 0
    comments_count: int = 0
    views_count: int = 0
    flags_count: int = 0
    is_flagged: bool = False
    user: Optional[UserSummary] = None
    # Generation / versioning
    version: int = 1
    draft_reason: Optional[str] = None

    # Allow model attributes-to-schema and ignore unknown extras
    model_config = dict(from_attributes=True, extra="ignore")

# Schema for paginated lists of stories
class StoryList(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[StoryOut] # Uses our new, unified StoryOut schema

    class Config:
        from_attributes = True

