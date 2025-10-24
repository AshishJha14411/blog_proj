import enum
from sqlalchemy import Column, String, ForeignKey, DateTime, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from app.core.database import Base

# Enum for the status of the request
class RequestStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class CreatorRequest(Base):
    __tablename__ = "creator_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # The user who is making the request
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True)
    
    # The current status of the request
    status = Column(Enum(RequestStatus), default=RequestStatus.PENDING, nullable=False, index=True)
    
    # The user's reason for wanting to be a creator
    reason = Column(Text, nullable=True)
    
    # The admin/moderator who reviewed the request
    reviewed_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # --- Relationships ---
    # Link back to the user who made the request
    user = relationship("User", foreign_keys=[user_id])
    
    # Link back to the admin who reviewed it
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])
