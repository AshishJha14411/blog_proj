from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class FlagCreate(BaseModel):
    reason: str = Field(..., min_length=3, max_length=500)

class FlagOut(BaseModel):
    id: int
    flagged_by_user_id: int
    post_id: Optional[int]
    comment_id: Optional[int]
    reason: str
    status: str
    resolved_by: Optional[int]
    created_at: datetime
    resolved_at: Optional[datetime]

    class Config:
        # Pydantic v2 replacement for the old orm_mode
        from_attributes = True

class FlagList(BaseModel):
    flags: List[FlagOut]

class FlagResolveRequest(BaseModel):
    # use `pattern=` instead of the removed `regex=`
    status: str = Field(..., pattern="^(resolved|ignored)$")

class ModerationDecision(BaseModel):
    note: Optional[str] = None   # for approve
    reason: Optional[str] = None # for reject
