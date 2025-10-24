from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
import uuid
from app.schemas.admin import (
    AdminUserOut, AdminUserUpdate,
    AuditLogOut, AuditLogList
)
from app.services.admin import (
    list_users, update_user,
    soft_delete_user, list_audit_logs
)
from app.models.user import User
from app.dependencies import get_db, require_roles , get_current_user
from app.schemas.admin import CreatorRequestCreate, CreatorRequestOut, CreatorRequestReview
from app.services.admin import (
    create_creator_request, 
    get_pending_creator_requests, 
    review_creator_request
)

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(require_roles("superadmin"))]
)

# 1. List all users
@router.get(
    "/users/",
    response_model=List[AdminUserOut],
    status_code=status.HTTP_200_OK
)
def admin_list_users(db: Session = Depends(get_db)):
    return list_users(db)

# 2. Update user (role / active status)
@router.patch(
    "/users/{user_id}",
    response_model=AdminUserOut,
    status_code=status.HTTP_200_OK
)
def admin_update_user(
    user_id: int,
    data: AdminUserUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return update_user(
        db,
        user_id,
        role_id=data.role_id,
        is_active=data.is_active,
        actor_id=current_user.id
    )

# 3. Soft-delete user
@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
def admin_delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    soft_delete_user(db, user_id, actor_id=current_user.id)

# 4. View audit logs
@router.get(
    "/audit-logs/",
    response_model=AuditLogList,
    status_code=status.HTTP_200_OK
)
def admin_audit_logs(db: Session = Depends(get_db)):
    logs = list_audit_logs(db)
    return AuditLogList(logs=logs)


# --- A new dependency for protecting admin routes ---
def get_current_admin_user(current_user: User = Depends(get_current_user)):
    if current_user.role.name not in ["moderator", "superadmin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform this action."
        )
    return current_user

# --- Router Setup ---
router = APIRouter(prefix="/admin", tags=["Admin"])
user_router = APIRouter(tags=["User Features"]) # A separate router for the user-facing part

# --- User-Facing Endpoint ---

@router.post(
    "/creator-requests",
    response_model=CreatorRequestOut,
    status_code=status.HTTP_201_CREATED
)
def submit_creator_request(
    data: CreatorRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Endpoint for a user to submit a request to become a creator."""
    return create_creator_request(db=db, user=current_user, data=data)

# --- Admin-Facing Endpoints ---

@router.get(
    "/creator-requests/pending", 
    response_model=List[CreatorRequestOut]
)
def list_pending_requests(
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """Admin endpoint to list all pending creator requests."""
    return get_pending_creator_requests(db=db)

@router.post(
    "/creator-requests/{request_id}/review", 
    response_model=CreatorRequestOut
)
def review_request(
    request_id: uuid.UUID,
    data: CreatorRequestReview,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """Admin endpoint to approve or reject a creator request."""
    return review_creator_request(db=db, request_id=request_id, admin_user=admin_user, data=data)
