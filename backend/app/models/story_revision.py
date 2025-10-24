# app/models/story_revision.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
from sqlalchemy.dialects.postgresql import UUID
import uuid
class StoryRevision(Base):
    __tablename__ = "story_revisions"

    id =  Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    stories_id = Column(UUID(as_uuid=True), ForeignKey("stories.id"), index=True, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False) 
    version = Column(Integer, nullable=False)           
    content = Column(Text, nullable=False)
    prompt = Column(Text, nullable=True)
    feedback = Column(Text, nullable=True)
    model_name = Column(String, nullable=True)
    provider_message_id = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    story = relationship("Story", back_populates="revisions")
