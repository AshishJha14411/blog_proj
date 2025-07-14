from sqlalchemy import Column, Integer, ForeignKey, DateTime
from datetime import datetime
from app.core.database import Base

class ViewHistory(Base):
    __tablename__ = "view_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    viewed_at = Column(DateTime, default=datetime.utcnow)