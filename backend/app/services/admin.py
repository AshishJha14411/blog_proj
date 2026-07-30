# app/services/admin.py
from datetime import datetime
from app.utils.time import utcnow
from uuid import UUID
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status

from app.models.role import Role
from app.models.creator_request import CreatorRequest, RequestStatus
from app.schemas.admin import CreatorRequestCreate, CreatorRequestReview
from app.models.user import User
from app.models.audit_log import AuditLog
from app.authz import Perm, has_perm

def list_users(db: Session, limit: int = 50, offset: int = 0):
    # W5: bounded — unbounded .all() is a time bomb as user counts grow.
    return (
        db.query(User)
        .order_by(User.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

def update_user(
    db: Session,
    user_id: UUID,
    role_id: UUID | None = None,
    is_disabled: bool | None = None,
    actor_id: UUID | None = None,
) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")

    # Bail out early if the caller would lock themselves (or every superadmin)
    # out of the system. A wrong click on the admin panel should not be able
    # to destroy the last root account.
    superadmin_role = db.query(Role).filter(Role.name == "superadmin").first()
    is_super = bool(superadmin_role and user.role_id == superadmin_role.id)

    demoting = (
        role_id is not None
        and superadmin_role is not None
        and is_super
        and role_id != superadmin_role.id
    )
    disabling = is_disabled is True and not user.is_disabled

    if is_super and (demoting or disabling):
        if actor_id is not None and actor_id == user.id:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Superadmins cannot demote or disable themselves.",
            )
        active_supers = (
            db.query(User)
            .filter(User.role_id == superadmin_role.id, User.is_disabled.is_(False))
            .count()
        )
        if active_supers <= 1:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Refusing to remove the last active superadmin.",
            )

    if role_id is not None:
        # G12: verify the role exists before assignment; otherwise the FK
        # violation surfaces as an opaque 500 on commit.
        if not db.get(Role, role_id):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Unknown role_id")
        user.role_id = role_id
    if is_disabled is not None:
        user.is_disabled = is_disabled

    db.commit()
    db.refresh(user)

    # Record in audit log (use JSON fields that actually exist on the model)
    audit = AuditLog(
        actor_user_id=actor_id,
        action="update_user",
        target_type="user",
        target_id=str(user_id),
        after_state={
            "role_id": str(role_id) if role_id is not None else None,
            "is_disabled": is_disabled, 
        },
        timestamp=utcnow(),
    )
    db.add(audit)
    db.commit()
    return user

def soft_delete_user(
    db: Session,
    user_id: UUID,
    actor_id: UUID,
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")

    user.is_disabled = True 
    db.commit()

    audit = AuditLog(
        actor_user_id=actor_id,
        action="soft_delete_user",
        target_type="user",
        target_id=str(user_id),
        after_state={"is_disabled": True}, 
        timestamp=utcnow(),
    )
    db.add(audit)
    db.commit()

def list_audit_logs(db: Session, limit: int = 50, offset: int = 0):
    # W5: bounded.
    return (
        db.query(AuditLog)
        .order_by(AuditLog.timestamp.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

def create_creator_request(db: Session, user: User, data: CreatorRequestCreate) -> CreatorRequest:
    # Only plain users can request creator access — the CREATOR_REQUEST
    # permission is granted to the "user" role only (creators+ already have it).
    if not has_perm(user, Perm.CREATOR_REQUEST):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already a creator or have higher permissions."
        )

    # Existing pending?
    existing_request = (
        db.query(CreatorRequest)
        .filter(CreatorRequest.user_id == user.id,
                CreatorRequest.status == RequestStatus.PENDING)
        .first()
    )
    if existing_request:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have a pending creator request."
        )

    new_request = CreatorRequest(user_id=user.id, reason=data.reason)
    db.add(new_request)
    db.commit()
    db.refresh(new_request)
    return new_request

def get_pending_creator_requests(db: Session) -> list[CreatorRequest]:
    return (
        db.query(CreatorRequest)
        .options(joinedload(CreatorRequest.user))
        .filter(CreatorRequest.status == RequestStatus.PENDING)
        .all()
    )

def review_creator_request(
    db: Session,
    request_id: UUID,
    admin_user: User,
    data: CreatorRequestReview
) -> CreatorRequest:
    req = (
        db.query(CreatorRequest)
        .filter(CreatorRequest.id == request_id)
        .first()
    )
    if not req or req.status != RequestStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pending creator request not found."
        )

    action = (data.action or "").lower()
    if action == "approve":
        creator_role = db.query(Role).filter(Role.name == "creator").first()
        if not creator_role:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Creator role not found.")
        req.user.role_id = creator_role.id
        req.status = RequestStatus.APPROVED
    elif action == "reject":
        req.status = RequestStatus.REJECTED
    else:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid action. Must be 'approve' or 'reject'.")

    req.reviewed_by_id = admin_user.id
    req.reviewed_at = utcnow()
    db.commit()
    db.refresh(req)
    return req
