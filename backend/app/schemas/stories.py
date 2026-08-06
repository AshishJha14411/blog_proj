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
    # /** WHY: optional — the genre is converted into tags automatically
    #     (see `tags_from_genre`), so a generated story is never untagged.
    #     Anything supplied here is merged in and normalised the same way. **/
    tag_names: List[constr(max_length=50)] = Field(default_factory=list)
    temperature: Optional[float] = Field(default=0.8, ge=0.0, le=2.0)
    # Default None so the LLM adapter falls back to settings.LLM_MODEL —
    # the single source of truth. A hardcoded default here (previously
    # "gpt-4o-mini", an OpenAI name sent to the Gemini provider) silently
    # overrides the configured model and 404s.
    model_name: Optional[constr(max_length=100)] = None
    cover_image_url: Optional[HttpUrl] = None

class StoryFeedbackIn(BaseModel):
    feedback: FeedbackText
    # Optional length override for "regenerate with feedback". Without this the
    # revision is locked to whatever length the story was first generated at, so
    # the length control on the preview page had no effect. Omitted => keep the
    # story's existing length.
    length_label: Optional[Literal["flash","short","medium","long"]] = None

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
    # AI-generation metadata — present on AI stories, null on human ones. These
    # exist on the ORM model and the edit UI reads them; they were previously
    # NOT exposed here, so the frontend silently read `undefined` (real drift,
    # surfaced by the generated-type adoption). Now part of the contract.
    genre: Optional[str] = None
    tone: Optional[str] = None
    length_label: Optional[str] = None
    summary: Optional[str] = None
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
    @field_validator("status", "source", "length_label", mode="before")
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
    # Opaque cursor for the NEXT page (keyset pagination). Null when there are
    # no more rows, or when the caller used offset pagination. Pass it back as
    # `?cursor=` to fetch the next page in O(1) regardless of depth.
    next_cursor: Optional[str] = None

    class Config:
        from_attributes = True

