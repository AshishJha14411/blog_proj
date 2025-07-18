from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.schemas.admin import (
    AdminUserOut, AdminUserUpdate,
    AuditLogOut, AuditLogList
)
from app.services.admin import (
    list_users, update_user,
    soft_delete_user, list_audit_logs
)
from app.dependencies import get_db, require_roles
from app.services.auth import get_current_user

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
