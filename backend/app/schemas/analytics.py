from pydantic import BaseModel
from typing import List
from datetime import date, datetime

class DayCount(BaseModel):
    day: date
    count: int

class PostsDaily(BaseModel):
    stats: List[DayCount]

class UsersDaily(BaseModel):
    stats: List[DayCount]

class FlagsBreakdown(BaseModel):
    total: int
    ai_flags: int
    human_flags: int

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

class ModerationLogs(BaseModel):
    logs: List[AuditLogOut]

class ClicksDaily(BaseModel):
    stats: List[DayCount]
