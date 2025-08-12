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


class DailyMetric(BaseModel):
    day: date
    new_users: int
    logins: int
    posts_created: int
    flags_created: int
    ai_flags: int
    human_flags: int
    dau: int
    posts_viewed: int
    likes: int
    comments: int
    ad_impressions: int
    ad_clicks: int

class AnalyticsSeries(BaseModel):
    items: List[DailyMetric]
