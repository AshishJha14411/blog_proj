from sqlalchemy import Column, Integer, Date, Boolean
from datetime import date,datetime
from app.core.database import Base

class AnalyticsCache(Base):
    __tablename__ = "analytics_cache"
    
    id = Column(Integer, primary_key=True, index=True)
    day = Column(Date, unique=True, nullable=False)
    new_users = Column(Integer, default=0)
    logins = Column(Integer, default=0)
    posts_created = Column(Integer, default=0)
    flags_created = Column(Integer, default=0)
    ai_flags = Column(Integer, default=0)
    human_flags = Column(Integer, default=0)