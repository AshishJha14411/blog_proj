from sqlalchemy import (
    Column, Integer, String, DateTime, Boolean, JSON, ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..core.database import Base
from sqlalchemy.dialects.postgresql import UUID
import uuid

class OAuthAccount(Base):
    __tablename__ = "oauth_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    provider = Column(String(50), nullable=False)   # "google", "apple", ...
    subject = Column(String(255), nullable=False)   # stable OIDC 'sub' from provider
    __table_args__ = (UniqueConstraint("provider", "subject", name="uq_provider_subject"),)

    account_email = Column(String)                  # email reported by provider at sign-in
    email_verified = Column(Boolean, default=False)
    profile = Column(JSON)                          # snapshot of claims (name, picture, locale)

    access_token = Column(String)
    refresh_token = Column(String)
    expires_at = Column(DateTime(timezone=True))
    scope = Column(String)
    token_type = Column(String)                     # usually "Bearer"

    last_login_at = Column(DateTime(timezone=True))
    login_count = Column(Integer, default=0)
    is_disabled = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(),
                        onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="oauth_accounts")
