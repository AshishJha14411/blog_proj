from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.schemas.user import UserSummary

class FlagCreate(BaseModel):
    reason: str = Field(..., min_length=3, max_length=500)

    class Config:
        from_attributes = True

class FlagOut(BaseModel):
    id: str
    flagged_by_user_id: str
    story_id: Optional[str] = None
    comment_id: Optional[str] = None
    reason: str
    status: str
    resolved_by: Optional[str] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None

    # ✅ make this optional; many queries don’t join the user
    flagged_by: Optional[UserSummary] = None

    class Config:
        from_attributes = True

class FlagList(BaseModel):
    flags: List[FlagOut]

class FlagResolveRequest(BaseModel):
    status: str = Field(..., pattern="^(resolved|ignored)$")

class ModerationDecision(BaseModel):
    note: Optional[str] = None
    reason: Optional[str] = None
