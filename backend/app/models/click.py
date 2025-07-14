from sqlalchemy import Column, Integer, ForeignKey, String, DateTime
from datetime import datetime
from app.core.database import Base

class Click(Base):
    __tablename__ = "clicks"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    clicked_at = Column(DateTime, default=datetime.utcnow)