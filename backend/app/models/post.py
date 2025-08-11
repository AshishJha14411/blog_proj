from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text, Enum, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
import enum

class FlagSource(enum.Enum):
    ai = "ai"
    user = "user"
    none = "none"

class ContentSource(enum.Enum):
    ai = "ai"
    user = "user"


class StoryStatus(enum.Enum):
    draft = "draft"             # just generated, not published
    generated = "generated"     # AI output saved, pending review/edit
    published = "published"     # visible to all
    rejected = "rejected"       # flagged/hidden


class LengthLabel(enum.Enum):
    flash = "flash"   # ~<800 words
    short = "short"   # ~800-1500
    medium = "medium" # ~1500-3000
    long = "long"     # >3000


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    header = Column(String, nullable=True)
    content = Column(Text, nullable=False)
    cover_image_url = Column(String, nullable=True)
    is_published = Column(Boolean, default=True)
    is_flagged = Column(Boolean, default=False)
    flag_source = Column(Enum(FlagSource), default=FlagSource.none)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True, index=True)
    
    user = relationship("User", back_populates="posts")
    tags = relationship("Tag", secondary="post_tags", back_populates="posts")
    likes = relationship("Like", back_populates="post")
    bookmarks = relationship("Bookmark", back_populates="post")
      # RELATIONSHIPS
    user = relationship("User", back_populates="posts")
    tags = relationship("Tag", secondary="post_tags", back_populates="posts")
    likes = relationship("Like", back_populates="post")
    bookmarks = relationship("Bookmark", back_populates="post")

  
    # Who created the content (AI vs user)
    source = Column(Enum(ContentSource), default=ContentSource.user, index=True)

    # Story metadata
    genre = Column(String, nullable=True, index=True)        # e.g. "sci-fi"
    tone = Column(String, nullable=True, index=True)         # e.g. "dark"
    length_label = Column(Enum(LengthLabel), nullable=True)  # flash/short/...

    summary = Column(String, nullable=True)                  # short description/blurb
    words_count = Column(Integer, default=0)                 # quick analytics

    # Generation workflow
    status = Column(Enum(StoryStatus), default=StoryStatus.draft, index=True)
    prompt = Column(Text, nullable=True)                     # theme/instructions
    model_name = Column(String, nullable=True)               # e.g. "gpt-4o-mini"
    temperature = Column(Float, nullable=True)
    provider_message_id = Column(String, nullable=True)      # LLM response id

    # Feedback + revisions
    parent_id = Column(Integer, ForeignKey("posts.id"), nullable=True)  # regen from which post
    version = Column(Integer, default=1)
    last_feedback = Column(Text, nullable=True)
   
    revisions = relationship("StoryRevision", back_populates="post", cascade="all, delete-orphan")
