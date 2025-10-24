from sqlalchemy import Column, Integer, ForeignKey, DateTime, String
from datetime import datetime
from app.core.database import Base
from sqlalchemy.dialects.postgresql import UUID
import uuid
class ViewHistory(Base):
    __tablename__ = "view_history"

    id =  Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    story_id = Column(UUID(as_uuid=True), ForeignKey("stories.id"), nullable=False)
    viewed_at = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String, nullable=True) 
    user_agent = Column(String, nullable=True)