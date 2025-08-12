from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional, Tuple, List
from app.models.notification import Notification

def notify(
    db: Session,
    recipient_id: int,
    action: str,
    *,
    actor_id: Optional[int] = None,
    target_type: Optional[str] = None,
    target_id: Optional[int] = None
) -> Notification:
    n = Notification(
        recipient_id=recipient_id,
        actor_id=actor_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        is_read=False
    )
    db.add(n)
    db.commit()
    db.refresh(n)
    return n

def list_my_notifications(
    db: Session,
    user_id: int,
    limit: int,
    offset: int,
    unread_only: bool = False
) -> Tuple[int, List[Notification]]:
    q = db.query(Notification).filter(Notification.recipient_id == user_id)
    if unread_only:
        q = q.filter(Notification.is_read == False)
    total = q.count()
    items = (q.order_by(desc(Notification.created_at))
               .offset(offset).limit(limit).all())
    return total, items

def mark_as_read(db: Session, notif_id: int, user_id: int) -> Notification:
    n = db.query(Notification).filter(
        Notification.id == notif_id,
        Notification.recipient_id == user_id
    ).first()
    if not n:
        return None
    if not n.is_read:
        n.is_read = True
        db.commit()
        db.refresh(n)
    return n

def mark_all_as_read(db: Session, user_id: int) -> int:
    updated = (db.query(Notification)
                 .filter(Notification.recipient_id == user_id,
                         Notification.is_read == False)
                 .update({Notification.is_read: True}))
    db.commit()
    return updated
