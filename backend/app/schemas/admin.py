# app/schemas/admin.py
from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, computed_field


# ----------------- Role -----------------

class RoleOut(BaseModel):
    id: UUID
    name: str

    model_config = dict(from_attributes=True)


# ----------------- Admin Users -----------------

class AdminUserOut(BaseModel):
    id: UUID
    username: str
    email: str
    role: Optional[RoleOut] = None

    # Your model stores this flag; keep it in the API
    is_disabled: bool = Field(default=False)

    # Many clients/tests expect is_active; compute it from is_disabled
    @computed_field  # type: ignore[misc]
    @property
    def is_active(self) -> bool:
        return not self.is_disabled

    model_config = dict(from_attributes=True)


class AdminUserUpdate(BaseModel):
    # Must be UUID (your models use UUID PKs)
    role_id: Optional[UUID] = None
    # Align to model & service (tests send/expect this)
    is_disabled: Optional[bool] = None


# ----------------- Audit Logs -----------------

class AuditLogOut(BaseModel):
    id: UUID
    actor_user_id: Optional[UUID] = None
    action: str
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    # Your service stores a dict in after_state
    after_state: Dict[str, Any] = Field(default_factory=dict)
    # details is not always present in your model -> make it optional
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime

    model_config = dict(from_attributes=True)


class AuditLogList(BaseModel):
    logs: List[AuditLogOut]


# ----------------- Creator Requests -----------------

class CreatorRequestCreate(BaseModel):
    reason: str


class CreatorRequestOut(BaseModel):
    id: UUID
    user_id: UUID
    reason: str
    status: str  # RequestStatus enum serialized as string
    created_at: datetime
    reviewed_by_id: Optional[UUID] = None
    reviewed_at: Optional[datetime] = None

    model_config = dict(from_attributes=True)


class CreatorRequestReview(BaseModel):
    action: str  # "approve" | "reject"
