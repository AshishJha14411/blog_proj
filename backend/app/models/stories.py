from sqlalchemy import (
    Column, Integer, String, Boolean, ForeignKey, DateTime,
    Text, Enum, Float
)
from app.utils.time import utcnow
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
import enum
from sqlalchemy.dialects.postgresql import UUID
import uuid

# --- Enums for Story Model ---

class FlagSource(enum.Enum):
    ai = "ai"
    user = "user"
    none = "none"

class ContentSource(enum.Enum):
    ai = "ai"
    user = "user"

class StoryStatus(enum.Enum):
    """
    /** WHY: adds `pending` for stories awaiting the async moderation task
        (UPGRADE_PLAN Phase 2 AI moderation migration). Existing values keep
        their meanings — the state machine is now:
            created  → pending  → published | rejected
            AI-gen'd → generated → (as above once publish_now is set)  **/
    """
    draft = "draft"
    pending = "pending"       # awaiting AI moderation
    generated = "generated"
    published = "published"
    rejected = "rejected"

class LengthLabel(enum.Enum):
    flash = "flash"
    short = "short"
    medium = "medium"
    long = "long"

# --- Story Model Definition ---

class Story(Base):
    __tablename__ = "stories"

    # Core Columns
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False) # Assuming users.id is also UUID
    title = Column(String, nullable=False)
    header = Column(String, nullable=True)
    content = Column(Text, nullable=False)
    cover_image_url = Column(String, nullable=True)
    
    # Status & Visibility
    is_published = Column(Boolean, default=True)
    is_flagged = Column(Boolean, default=False)
    flag_source = Column(Enum(FlagSource), default=FlagSource.none)
    status = Column(Enum(StoryStatus), default=StoryStatus.draft, index=True)

    # Timestamps
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    deleted_at = Column(DateTime, nullable=True, index=True)
    
    # Relationships
    user = relationship("User", back_populates="stories")
    tags = relationship("Tag", secondary="story_tags", back_populates="stories")
    likes = relationship("Like", back_populates="story")
    bookmarks = relationship("Bookmark", back_populates="story")
    revisions = relationship("StoryRevision", back_populates="story", cascade="all, delete-orphan")

    # Content Source
    source = Column(Enum(ContentSource), default=ContentSource.user, index=True)

    # Story Metadata
    genre = Column(String, nullable=True, index=True)
    tone = Column(String, nullable=True, index=True)
    length_label = Column(Enum(LengthLabel), nullable=True)
    summary = Column(String, nullable=True)
    words_count = Column(Integer, default=0)

    # Generation Workflow Details
    prompt = Column(Text, nullable=True)
    model_name = Column(String, nullable=True)
    temperature = Column(Float, nullable=True)
    provider_message_id = Column(String, nullable=True)

    # Feedback & Revisions
    parent_id = Column(UUID(as_uuid=True), ForeignKey("stories.id"), nullable=True) # Corrected: self-referencing FK
    version = Column(Integer, default=1)          # revision number (regenerate bumps it)
    last_feedback = Column(Text, nullable=True)

    # Optimistic-lock counter — SEPARATE from `version` (which is a revision
    # number). SQLAlchemy adds `WHERE row_version = :current` to every UPDATE
    # and increments it; if a concurrent write already bumped it, the UPDATE
    # matches 0 rows and raises StaleDataError. Lost-update prevention without
    # row locks. See __mapper_args__ below.
    row_version = Column(Integer, nullable=False, default=1)

    __mapper_args__ = {"version_id_col": row_version}
