from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from datetime import datetime
from app.core.database import Base
from sqlalchemy.dialects.postgresql import UUID
import uuid
class Ads(Base):
    __tablename__ = "ads"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    advertiser_name = Column(String, nullable=True)
    ad_content = Column(Text, nullable=True)
    image_url = Column(String, nullable=True)
    destination_url = Column(String, nullable=False)
    weight = Column(Integer, default=1, nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    start_at = Column(DateTime, nullable=True)
    end_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)