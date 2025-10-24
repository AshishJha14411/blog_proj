from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.role import Role
from app.models.creator_request import CreatorRequest, RequestStatus
from app.schemas.admin import CreatorRequestCreate, CreatorRequestReview
from app.models.user import User
from app.models.audit_log import AuditLog
import uuid
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


def create_creator_request(db: Session, user: User, data: CreatorRequestCreate) -> CreatorRequest:
    """Allows a user to submit a request to become a creator."""
    
    # 1. Check if user is already a creator or higher
    if user.role.name in ["creator", "moderator", "superadmin"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already a creator or have higher permissions."
        )

    # 2. Check for an existing pending request
    existing_request = db.query(CreatorRequest).filter(
        CreatorRequest.user_id == str(user.id),
        CreatorRequest.status == RequestStatus.PENDING
    ).first()
    if existing_request:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have a pending creator request."
        )

    # 3. Create the new request
    new_request = CreatorRequest(
        user_id=str(user.id),
        reason=data.reason
    )
    db.add(new_request)
    db.commit()
    db.refresh(new_request)
    return new_request

def get_pending_creator_requests(db: Session) -> list[CreatorRequest]:
    """Fetches all creator requests with a 'pending' status for moderation."""
    return db.query(CreatorRequest).filter(CreatorRequest.status == RequestStatus.PENDING).all()

def review_creator_request(
    db: Session, 
    request_id: uuid.UUID, 
    admin_user: User, 
    data: CreatorRequestReview
) -> CreatorRequest:
    """Allows an admin/moderator to approve or reject a creator request."""
    
    # 1. Find the request
    request = db.query(CreatorRequest).filter(CreatorRequest.id == request_id).first()
    if not request or request.status != RequestStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pending creator request not found."
        )
        
    # 2. Process the action
    if data.action.lower() == "approve":
        # Find the "creator" role
        creator_role = db.query(Role).filter(Role.name == "creator").first()
        if not creator_role:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Creator role not found.")
            
        # Upgrade the user's role
        request.user.role_id = creator_role.id
        request.status = RequestStatus.APPROVED
        
    elif data.action.lower() == "reject":
        request.status = RequestStatus.REJECTED
    else:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid action. Must be 'approve' or 'reject'.")

    # 3. Log the review details and commit
    request.reviewed_by_id = admin_user.id
    request.reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(request)
    return request
