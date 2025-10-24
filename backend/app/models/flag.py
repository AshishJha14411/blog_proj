from sqlalchemy import Column, Integer, ForeignKey, Text, String, DateTime
from datetime import datetime
from app.core.database import Base
from sqlalchemy.dialects.postgresql import UUID
import uuid
class Flag(Base):
    __tablename__ = "flags"

    id =  Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    flagged_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    story_id = Column(UUID(as_uuid=True), ForeignKey("stories.id"), nullable=True)
    comment_id = Column(UUID(as_uuid=True), ForeignKey("comments.id"), nullable=True)
    reason = Column(Text, nullable=False)
    status = Column(String, default="open")
    resolved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)