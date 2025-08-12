from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from datetime import datetime
from app.core.database import Base

class Ad(Base):
    __tablename__ = "ads"

    id = Column(Integer, primary_key=True, index=True)
    advertiser_name = Column(String, nullable=True)
    ad_content = Column(Text, nullable=True)
    image_url = Column(String, nullable=True)
    destination_url = Column(String, nullable=False)

    slot = Column(String, nullable=False, index=True)  # e.g., story_top, story_inline
    tags = Column(String, nullable=True)

    weight = Column(Integer, default=1, nullable=False)
    active = Column(Boolean, default=True, nullable=False)

    start_at = Column(DateTime, nullable=True)
    end_at = Column(DateTime, nullable=True)

    utm_source = Column(String, nullable=True)
    utm_medium = Column(String, nullable=True)
    utm_campaign = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
