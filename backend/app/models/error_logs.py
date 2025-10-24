from sqlalchemy import Column, Integer, String, DateTime, Text, JSON
from sqlalchemy.sql import func
from app.core.database import Base
from sqlalchemy.dialects.postgresql import UUID
import uuid
class ErrorLog(Base):
    __tablename__ = "error_logs"

    id =  Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Severity level for easy filtering (e.g., "INFO", "WARNING", "ERROR", "CRITICAL")
    level = Column(String(50), nullable=False, index=True)
    
    # The short, human-readable error message.
    message = Column(String(255), nullable=False)
    
    # The full technical stack trace for deep debugging.
    traceback = Column(Text, nullable=True)
    
    # A JSON blob to store the context of the request when the error occurred.
    # (e.g., URL, method, headers, user_id if available)
    request_context = Column(JSON, nullable=True)
    error_hash = Column(String(64), nullable=False, unique=True, index=True) # A SHA-256 hash
    count = Column(Integer, default=1, nullable=False)
    last_seen_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Renamed for clarity
    first_seen_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
