from pydantic import BaseModel, HttpUrl, Field, constr, field_validator
from typing import List, Optional, Literal
from datetime import datetime
from uuid import UUID # Import UUID for type hinting if needed, though str is used for JSON


# Length caps: keep DB rows reasonable and prevent oversized-input DoS.
# Bumping any of these is a real product decision, not a lint fix.
StoryTitle = constr(strip_whitespace=True, min_length=1, max_length=300)
StoryHeader = constr(strip_whitespace=True, max_length=500)
StoryContent = constr(min_length=1, max_length=100_000)
TagName = constr(strip_whitespace=True, min_length=1, max_length=50)
PromptText = constr(strip_whitespace=True, min_length=1, max_length=20_000)
FeedbackText = constr(strip_whitespace=True, min_length=1, max_length=5_000)

# --- Nested Schemas for Clean Responses ---
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
    title: StoryTitle
    header: Optional[StoryHeader] = None
    content: StoryContent
    cover_image_url: Optional[HttpUrl] = None
    tag_names: List[TagName] = Field(default_factory=list, max_length=20)
    is_published: bool = True

class StoryUpdate(BaseModel):
    title: Optional[StoryTitle] = None
    header: Optional[StoryHeader] = None
    content: Optional[StoryContent] = None
    cover_image_url: Optional[HttpUrl] = None
    tag_names: Optional[List[TagName]] = Field(default=None, max_length=20)
    is_published: Optional[bool] = None

# --- AI Generation Input Schemas (Added Back) ---

class StoryGenerateIn(BaseModel):
    title: Optional[StoryTitle] = None
    summary: Optional[StoryHeader] = None  # short description/blurb the user writes
    prompt: PromptText                     # theme/instructions
    genre: Optional[constr(max_length=100)] = None
    tone: Optional[constr(max_length=100)] = None
    length_label: Optional[Literal["flash","short","medium","long"]] = None
    publish_now: bool = False
    temperature: Optional[float] = Field(default=0.8, ge=0.0, le=2.0)
    # Default None so the LLM adapter falls back to settings.LLM_MODEL —
    # the single source of truth. A hardcoded default here (previously
    # "gpt-4o-mini", an OpenAI name sent to the Gemini provider) silently
    # overrides the configured model and 404s.
    model_name: Optional[constr(max_length=100)] = None
    cover_image_url: Optional[HttpUrl] = None

class StoryFeedbackIn(BaseModel):
    feedback: FeedbackText

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
    # Lifecycle state — draft | pending | generated | published | rejected.
    # Lets the frontend distinguish "under review" from "rejected" from
    # "draft", all of which otherwise collapse to is_published=False.
    status: Optional[str] = None
    # Generation / versioning
    version: int = 1
    draft_reason: Optional[str] = None

    # status is a StoryStatus enum on the ORM model; coerce to its string
    # value so both model_validate() and manual construction accept it.
    @field_validator("status", "source", mode="before")
    @classmethod
    def _enum_to_value(cls, v):
        return v.value if hasattr(v, "value") else v

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

