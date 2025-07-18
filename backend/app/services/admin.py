from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.user import User
from app.models.audit_log import AuditLog

def list_users(db: Session):
    return db.query(User).all()

def update_user(
    db: Session,
    user_id: int,
    role_id: int | None = None,
    is_active: bool | None = None,
    actor_id: int = None
) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")
    if role_id is not None:
        user.role_id = role_id
    if is_active is not None:
        user.is_active = is_active
    db.commit()
    db.refresh(user)
    # record in audit log
    audit = AuditLog(
        actor_user_id=actor_id,
        action="update_user",
        target_type="user",
        target_id=user_id,
        details=f"role_id={role_id},is_active={is_active}",
        timestamp=datetime.utcnow()
    )
    db.add(audit)
    db.commit()
    return user

def soft_delete_user(
    db: Session,
    user_id: int,
    actor_id: int
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")
    user.is_active = False
    db.commit()
    # audit the deletion
    audit = AuditLog(
        actor_user_id=actor_id,
        action="soft_delete_user",
        target_type="user",
        target_id=user_id,
        details="soft-deleted",
        timestamp=datetime.utcnow()
    )
    db.add(audit)
    db.commit()

def list_audit_logs(db: Session):
    return db.query(AuditLog).order_by(AuditLog.timestamp.desc()).all()
