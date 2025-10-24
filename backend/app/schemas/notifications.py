from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID
class NotificationOut(BaseModel):
    id: UUID
    recipient_id: UUID
    actor_id: Optional[UUID] = None
    action: str
    target_type: Optional[str] = None
    target_id: Optional[UUID] = None
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True

class NotificationList(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[NotificationOut]
