from sqlalchemy import Column, Integer, String, DateTime
from app.core.database import Base

class TokenBlacklist(Base):
    __tablename__ = "token_blacklist"

    id = Column(Integer, primary_key=True, index=True)
    jti = Column(String, unique=True, nullable=False, index=True) # "JWT ID" claim
    expires_at = Column(DateTime, nullable=False)