from sqlalchemy import Column, Integer, String, DateTime
from app.core.database import Base
from sqlalchemy.dialects.postgresql import UUID
import uuid
class TokenBlacklist(Base):
    __tablename__ = "token_blacklist"

    id =  Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    jti = Column(String, unique=True, nullable=False, index=True) # "JWT ID" claim
    expires_at = Column(DateTime, nullable=False)