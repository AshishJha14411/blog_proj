# app/services/admin.py
from datetime import datetime
from uuid import UUID
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.role import Role
from app.models.creator_request import CreatorRequest, RequestStatus
from app.schemas.admin import CreatorRequestCreate, CreatorRequestReview
from app.models.user import User
from app.models.audit_log import AuditLog

def list_users(db: Session):
    return db.query(User).all()

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

    if role_id is not None:
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
        timestamp=datetime.utcnow(),
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
        timestamp=datetime.utcnow(),
    )
    db.add(audit)
    db.commit()

def list_audit_logs(db: Session):
    return db.query(AuditLog).order_by(AuditLog.timestamp.desc()).all()

def create_creator_request(db: Session, user: User, data: CreatorRequestCreate) -> CreatorRequest:
    # Already creator or higher?
    if user.role.name in ["creator", "moderator", "superadmin"]:
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
    return db.query(CreatorRequest).filter(CreatorRequest.status == RequestStatus.PENDING).all()

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
    req.reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(req)
    return req
