"""User-facing webhook endpoint management.

POST   /webhooks       register an endpoint (returns the signing secret ONCE)
GET    /webhooks       list your endpoints (never returns the secret)
DELETE /webhooks/{id}  remove an endpoint
"""
from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_current_user
from app.models.user import User
from app.schemas.webhook import WebhookCreate, WebhookCreated, WebhookOut
from app.services import webhooks as webhook_service

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("", response_model=WebhookCreated, status_code=status.HTTP_201_CREATED)
def create_webhook(
    data: WebhookCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return webhook_service.create_endpoint(db, current_user, data)


@router.get("", response_model=List[WebhookOut])
def list_webhooks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return webhook_service.list_endpoints(db, current_user)


@router.delete("/{endpoint_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_webhook(
    endpoint_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    webhook_service.delete_endpoint(db, current_user, endpoint_id)
    return None
