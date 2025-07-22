from sqlalchemy import Column, Integer, ForeignKey, DateTime, String
from datetime import datetime
from app.core.database import Base

class ViewHistory(Base):
    __tablename__ = "view_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    viewed_at = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String, nullable=True) 
    user_agent = Column(String, nullable=True)