# app/models/ads.py

from sqlalchemy import Column, Integer, String
from app.core.database import Base

class Ad(Base):
    __tablename__ = "ads"

    id = Column(Integer, primary_key=True, index=True)
    advertiser_name = Column(String)
    ad_content = Column(String) 
    destination_url = Column(String, nullable=False)