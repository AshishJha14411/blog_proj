from sqlalchemy.orm import Session,selectinload
from sqlalchemy import desc,func
from typing import Optional, Tuple, List
from uuid import UUID

from app.models.notification import Notification


def notify(
    db: Session,
    recipient_id: UUID,
    action: str,
    *,
    actor_id: Optional[UUID] = None,
    target_type: Optional[str] = None,
    target_id: Optional[UUID] = None,
) -> Notification:
    """
    Create and persist a notification record.
    """
    n = Notification(
        recipient_id=recipient_id,
        actor_id=actor_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        is_read=False,
    )
    db.add(n)
    db.commit()
    db.refresh(n)
    return n


def list_my_notifications(db: Session, user_id: UUID, limit: int, offset: int, unread_only: bool = False) -> Tuple[int, List[Notification]]:
    q = db.query(Notification).filter(Notification.recipient_id == user_id)
    if unread_only:
        q = q.filter(Notification.is_read.is_(False))

    total = q.with_entities(func.count()).scalar()  # or q.count()
    print(f"User Id is {user_id}")
    items = (
        q.options(selectinload(Notification.actor))   # <-- if you’ll expose actor
         .order_by(desc(Notification.created_at))
         .offset(offset)
         .limit(limit)
         .all()
    )
    print(f"from the service of notification {total}, {items}")
    return total, items


def mark_as_read(db: Session, notif_id: UUID, user_id: UUID) -> Optional[Notification]:
    """
    Mark a single notification as read for the given user.
    """
    n = (
        db.query(Notification)
        .filter(Notification.id == notif_id, Notification.recipient_id == user_id)
        .first()
    )

    if not n:
        return None

    if not n.is_read:
        n.is_read = True
        db.commit()
        db.refresh(n)

    return n


def mark_all_as_read(db: Session, user_id: UUID) -> int:
    """
    Mark all notifications as read for the given user.
    """
    updated = (
        db.query(Notification)
        .filter(Notification.recipient_id == user_id, Notification.is_read.is_(False))
        .update({Notification.is_read: True}, synchronize_session=False)
    )
    db.commit()
    return updated
