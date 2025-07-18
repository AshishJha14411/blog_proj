from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from app.schemas.auth import UserProfile

class AdminUserOut(UserProfile):
    is_active: bool
    role_id: int

    class Config:
        from_attributes = True

class AdminUserUpdate(BaseModel):
    role_id: Optional[int]
    is_active: Optional[bool]

class AuditLogOut(BaseModel):
    id: int
    actor_user_id: int
    action: str
    target_type: str
    target_id: int
    details: str
    timestamp: datetime

    class Config:
        from_attributes = True

class AuditLogList(BaseModel):
    logs: List[AuditLogOut]
