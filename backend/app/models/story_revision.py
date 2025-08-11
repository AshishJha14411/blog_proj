# app/models/story_revision.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class StoryRevision(Base):
    __tablename__ = "story_revisions"

    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey("posts.id"), index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False) 
    version = Column(Integer, nullable=False)           
    content = Column(Text, nullable=False)
    prompt = Column(Text, nullable=True)
    feedback = Column(Text, nullable=True)
    model_name = Column(String, nullable=True)
    provider_message_id = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    post = relationship("Post", back_populates="revisions")
