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

from typing import List, Optional, Literal
from pydantic import BaseModel

class SeriesItem(BaseModel):
    ts: str  # ISO timestamp at bucket start
    metrics: dict[str, float]

class SeriesOut(BaseModel):
    items: List[SeriesItem]

class AdsCtrRow(BaseModel):
    ad_id: int
    slot: Optional[str]
    impressions: int
    clicks: int
    ctr: float

class FlagsByUserRow(BaseModel):
    user_id: int
    username: str
    total_flags: int
    ai_flags: int
    human_flags: int
    last_flag_at: str

class FlagsByUserOut(BaseModel):
    rows: List[FlagsByUserRow]

class ApprovalsByUserRow(BaseModel):
    user_id: int
    username: str
    approvals: int
    last_approval_at: Optional[str]

class ApprovalsByUserOut(BaseModel):
    rows: List[ApprovalsByUserRow]

class EventRow(BaseModel):
    id: int
    type: Literal["click","view","like","bookmark","flag","approve"]
    created_at: str
    user_id: Optional[int]
    username: Optional[str]
    post_id: Optional[int]
    post_title: Optional[str]
    meta: Optional[dict]

class EventsPage(BaseModel):
    total: int
    items: List[EventRow]