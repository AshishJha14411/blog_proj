from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from app.schemas.auth import UserProfile
from uuid import UUID
class AdminUserOut(UserProfile):
    is_active: bool
    role_id: UUID

    class Config:
        from_attributes = True

class AdminUserUpdate(BaseModel):
    role_id: Optional[int]
    is_active: Optional[bool]

class AuditLogOut(BaseModel):
    id: UUID
    actor_user_id: UUID
    action: str
    target_type: str
    target_id: UUID
    details: str
    timestamp: datetime

    class Config:
        from_attributes = True

class AuditLogList(BaseModel):
    logs: List[AuditLogOut]


class CreatorRequestCreate(BaseModel):
    reason: Optional[str] = None

# A summary of a user for nested responses
class UserSummary(BaseModel):
    id: UUID
    username: str

    class Config:
        from_attributes = True

# The full response model for a creator request
class CreatorRequestOut(BaseModel):
    id: UUID
    user: UserSummary
    status: str
    reason: Optional[str] = None

    class Config:
        from_attributes = True

# Schema for an admin reviewing a request
class CreatorRequestReview(BaseModel):
    action: str # Must be "approve" or "reject"