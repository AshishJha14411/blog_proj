from sqlalchemy import Column, Integer, ForeignKey, DateTime, UniqueConstraint
from datetime import datetime
from sqlalchemy.orm import relationship
from app.core.database import Base
from sqlalchemy.dialects.postgresql import UUID
import uuid
class Bookmark(Base):
    __tablename__ = "bookmarks"

    id =  Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    story_id = Column(UUID(as_uuid=True), ForeignKey("stories.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="bookmarks")
    story = relationship("Story", back_populates="bookmarks")
    __table_args__ = (UniqueConstraint('user_id', 'story_id', name='_user_story_bookmark_uc'),)