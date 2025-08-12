from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class NotificationOut(BaseModel):
    id: int
    recipient_id: int
    actor_id: Optional[int] = None
    action: str
    target_type: Optional[str] = None
    target_id: Optional[int] = None
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True

class NotificationList(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[NotificationOut]
