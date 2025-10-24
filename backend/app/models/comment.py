from sqlalchemy import Column, Integer, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
from sqlalchemy.dialects.postgresql import UUID
import uuid
class Comment(Base):
    __tablename__ = "comments"

    id =  Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    story_id = Column(UUID(as_uuid=True), ForeignKey("stories.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="comments")
    story = relationship("Story")