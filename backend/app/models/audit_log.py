from sqlalchemy import Column, Integer, String, DateTime, Text, Enum, JSON,ForeignKey
from sqlalchemy.dialects.postgresql import INET,UUID # A specific type for IP addresses
from app.core.database import Base
from datetime import datetime
import enum
import uuid
class AuditLogStatus(enum.Enum):
    SUCCESS = "success"
    FAILURE = "failure"

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # --- WHO ---
    # The user who performed the action.
    actor_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # --- WHAT ---
    # The action performed, e.g., "USER_CREATE", "POST_DELETE".
    action = Column(String, nullable=False, index=True)
    
    # --- ON WHAT ---
    # The type of object that was changed, e.g., "User", "Post".
    target_type = Column(String, nullable=True, index=True) 
    # The specific ID of the object. Can be nullable if action doesn't have a target.
    target_id = Column(String, nullable=True, index=True)
    
    # --- THE CHANGE (Most Useful Additions) ---
    # A JSON snapshot of the data BEFORE the change.
    before_state = Column(JSON, nullable=True)
    # A JSON snapshot of the data AFTER the change.
    after_state = Column(JSON, nullable=True)
    
    # --- CONTEXT (Where and How) ---
    # The IP address of the user who performed the action.
    ip_address = Column(String(45), nullable=True)
    # The user's browser/client information.
    user_agent = Column(String(255), nullable=True)
    
    # --- RESULT ---
    # Did the action succeed or fail?
    status = Column(Enum(AuditLogStatus), nullable=False, default=AuditLogStatus.SUCCESS)
    # Optional field for failure reason, e.g., "Permission Denied".
    status_reason = Column(Text, nullable=True)

    # You would still have your relationship to the User model
    # actor = relationship("User")