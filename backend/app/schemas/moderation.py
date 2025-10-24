from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.schemas.user import UserSummary
from uuid import UUID
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

    # Add nested user info for context
    flagged_by: UserSummary

    class Config:
        from_attributes = True

class FlagList(BaseModel):
    flags: List[FlagOut]

class FlagResolveRequest(BaseModel):
    # use `pattern=` instead of the removed `regex=`
    status: str = Field(..., pattern="^(resolved|ignored)$")

class ModerationDecision(BaseModel):
    note: Optional[str] = None   # for approve
    reason: Optional[str] = None # for reject
