from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime
from app.core.database import Base
from sqlalchemy.dialects.postgresql import UUID
import uuid
class Impression(Base):
    __tablename__ = "impressions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ad_id = Column(UUID(as_uuid=True), ForeignKey("ads.id", ondelete="CASCADE"), nullable=False, index=True)
    story_id = Column(UUID(as_uuid=True), ForeignKey("stories.id"), nullable=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)

    slot = Column(String, nullable=False)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)

    viewed_at = Column(DateTime, default=datetime.utcnow, index=True)
