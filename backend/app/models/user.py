from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
from app.models.role import Role
from sqlalchemy.dialects.postgresql import UUID
import uuid
class User(Base):
    __tablename__ = "users"

    id =  Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    is_verified = Column(Boolean, default=False)
    is_otp_verified = Column(Boolean, default=False)
    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id"), nullable=False)
    profile_image_url = Column(String, nullable=True)
    bio = Column(String, nullable=True)
    social_links = Column(JSON, nullable=True)
    total_posts = Column(Integer, default=0)
    total_likes = Column(Integer, default=0)
    total_comments = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    is_disabled = Column(Boolean, default=False)
    role = relationship(Role)
    stories = relationship("Story", back_populates="user", cascade="all, delete-orphan")

    # Other relationships
    likes = relationship("Like", back_populates="user", cascade="all, delete-orphan")
    bookmarks = relationship("Bookmark", back_populates="user", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="user", cascade="all, delete-orphan")
    
    oauth_accounts = relationship("OAuthAccount", back_populates="user", cascade="all, delete-orphan")
