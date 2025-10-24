from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from app.models.notification import Notification
from app.dependencies import get_db, get_current_user
from app.schemas.notifications import NotificationOut, NotificationList
from app.services.notifications import list_my_notifications, mark_as_read, mark_all_as_read
from app.models.user import User

router = APIRouter(prefix="/me/notifications", tags=["Notifications"])

@router.get("/", response_model=NotificationList)
def my_notifications(
    limit: int = Query(10, gt=0, le=100),
    offset: int = Query(0, ge=0),
    unread_only: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    total, items = list_my_notifications(db, current_user.id, limit, offset, unread_only)
    return NotificationList(total=total, limit=limit, offset=offset, items=items)

@router.post("/{notif_id}/read", response_model=NotificationOut)
def read_notification(
    notif_id: UUID,  # <-- was int
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    n = mark_as_read(db, notif_id, current_user.id)
    if not n:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )
    return n

@router.post("/read_all", response_model=dict)
def read_all_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    count = mark_all_as_read(db, current_user.id)
    return {"updated": count}


# in notifications router
@router.get("/unread_count", response_model=dict)
def unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    count = (
        db.query(Notification)
        .filter(Notification.recipient_id == current_user.id, Notification.is_read.is_(False))
        .count()
    )
    return {"count": count}
