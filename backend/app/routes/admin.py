# app/routes/admin.py
from typing import List
import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, status, HTTPException, Query
from sqlalchemy.orm import Session

from app.schemas.admin import (
    AdminUserOut, AdminUserUpdate,
    AuditLogList,
    CreatorRequestCreate, CreatorRequestOut, CreatorRequestReview
)
from app.services.admin import (
    list_users as svc_list_users,
    update_user as svc_update_user,
    soft_delete_user as svc_soft_delete_user,
    list_audit_logs as svc_list_audit_logs,
    create_creator_request as svc_create_creator_request,
    get_pending_creator_requests as svc_get_pending_creator_requests,
    review_creator_request as svc_review_creator_request,
)
from app.models.user import User
from app.dependencies import get_db, require_roles, get_current_user

# ---- Single router, keep protection here (superadmin-only for admin suite) ----
router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
)

# ---- Helper dependency for actions that allow moderator OR superadmin ----
def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role and current_user.role.name in ("moderator", "superadmin"):
        return current_user
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions.")

# ----------------- USERS MANAGEMENT (superadmin only) -----------------

@router.get(
    "/users/",
    response_model=List[AdminUserOut],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles("superadmin"))],
)
def admin_list_users(db: Session = Depends(get_db)):
    return svc_list_users(db)

@router.patch(
    "/users/{user_id}",
    response_model=AdminUserOut,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles("superadmin"))],
)
def admin_update_user(
    user_id: UUID,
    data: AdminUserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # AdminUserUpdate should expose role_id: UUID | None and is_disabled: bool | None
    updated = svc_update_user(
        db=db,
        user_id=user_id,
        role_id=data.role_id,
        is_disabled=data.is_disabled,
        actor_id=current_user.id,
    )
    return updated

@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles("superadmin"))],
)
def admin_delete_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc_soft_delete_user(db, user_id, actor_id=current_user.id)
    return None

@router.get(
    "/audit-logs/",
    response_model=AuditLogList,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles("superadmin"))],
)
def admin_audit_logs(db: Session = Depends(get_db)):
    logs = svc_list_audit_logs(db)
    return AuditLogList(logs=logs)

# ----------------- CREATOR REQUESTS -----------------
# Submit: any logged-in user
@router.post(
    "/creator-requests",
    response_model=CreatorRequestOut,
    status_code=status.HTTP_201_CREATED,
)
def submit_creator_request(
    data: CreatorRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return svc_create_creator_request(db=db, user=current_user, data=data)

# Pending & Review: moderator or superadmin
@router.get(
    "/creator-requests/pending",
    response_model=List[CreatorRequestOut],
)
def list_pending_requests(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    return svc_get_pending_creator_requests(db=db)

@router.post(
    "/creator-requests/{request_id}/review",
    response_model=CreatorRequestOut,
)
def review_request(
    request_id: UUID,
    data: CreatorRequestReview,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user),
):
    return svc_review_creator_request(db=db, request_id=request_id, admin_user=admin_user, data=data)
