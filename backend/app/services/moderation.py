from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import datetime
from typing import List, Tuple, Optional
import uuid
from app.models.tags import Tag
from app.models.flag import Flag
from app.models.stories import Story, StoryStatus
from app.models.comment import Comment
from app.models.user import User
from app.services.notifications import notify
from better_profanity import profanity

# Load default word list once at import time
profanity.load_censor_words()


# --- Flagging Logic ---

def flag_story(db: Session, story_id: uuid.UUID, reason: str, current_user: User) -> Flag:
    story = db.get(Story, story_id)
    if not story:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Story not found")
    
    flag = Flag(
        flagged_by_user_id=current_user.id,
        story_id=story_id,
        reason=reason.strip(),
        status="open"
    )
    db.add(flag)
    db.commit()
    db.refresh(flag)
    return flag

def flag_comment(db: Session, comment_id: uuid.UUID, reason: str, current_user: User) -> Flag:
    comment = db.get(Comment, comment_id)
    if not comment:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Comment not found")
        
    flag = Flag(
        flagged_by_user_id=current_user.id,
        comment_id=comment_id,
        reason=reason.strip(),
        status="open"
    )
    db.add(flag)
    db.commit()
    db.refresh(flag)
    return flag

def list_open_flags(db: Session) -> List[Flag]:
    return db.query(Flag).filter(Flag.status == "open").order_by(Flag.created_at.desc()).all()

# app/services/moderation.py
from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from app.models.flag import Flag
from app.models.user import User
from app.models.audit_log import AuditLog

VALID_FLAG_STATUSES = {"open", "resolved", "ignored"}

def resolve_flag(db: Session, flag_id: UUID, new_status: str, actor: User) -> Flag:
    """
    Update a flag's status with audit fields.
    - Valid statuses: open | resolved | ignored
    - When resolved/ignored -> set resolved_by and resolved_at
    - When open -> clear resolved_* fields
    """
    new_status = (new_status or "").lower()
    if new_status not in VALID_FLAG_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status. Must be one of: open, resolved, ignored."
        )

    flag = db.get(Flag, flag_id)
    if not flag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flag not found")

    before = {"status": flag.status}

    flag.status = new_status
    now = datetime.utcnow()

    if new_status in {"resolved", "ignored"}:
        # NOTE: model column is `resolved_by` (UUID), not `resolved_by_id`
        flag.resolved_by = actor.id
        flag.resolved_at = now
    else:  # "open"
        flag.resolved_by = None
        flag.resolved_at = None

    db.commit()
    db.refresh(flag)

    db.add(AuditLog(
        actor_user_id=actor.id,
        action="resolve_flag",
        target_type="flag",
        target_id=str(flag.id),
        after_state={"status": flag.status},
        timestamp=now,
        before_state={"before_state": before}
    ))
    db.commit()

    return flag


def approve_story(db: Session, story_id: uuid.UUID, moderator: User, note: str = "") -> Story:
    story = db.get(Story, story_id)
    if not story:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Story not found")

    story.status = StoryStatus.published
    story.is_published = True
    story.is_flagged = False
    _close_open_flags(db, story_id, moderator.id, "approved", note)
    db.commit()
    db.refresh(story)
    notify(db, recipient_id=story.user_id, actor_id=moderator.id, action="story_approved", target_type="story", target_id=story.id)
    return story

def reject_story(db: Session, story_id: uuid.UUID, moderator: User, reason: str) -> Story:
    story = db.get(Story, story_id)
    if not story:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Story not found")

    story.status = StoryStatus.rejected
    story.is_published = False
    story.is_flagged = True
    _close_open_flags(db, story_id, moderator.id, "rejected", reason)
    db.commit()
    db.refresh(story)
    notify(db, recipient_id=story.user_id, actor_id=moderator.id, action="story_rejected", target_type="story", target_id=story.id)
    return story

def _close_open_flags(db: Session, story_id: uuid.UUID, resolver_id: uuid.UUID, decision: str, note: str):
    flags = db.query(Flag).filter(Flag.story_id == story_id, Flag.status == "open").all()
    for f in flags:
        f.status = decision
        f.resolved_by_id = resolver_id
        f.resolved_at = datetime.utcnow()
        if note:
            f.reason = f"{f.reason or ''} | Moderator Note: {note}"

def moderation_queue(
    db: Session,
    status_filter: Optional[StoryStatus],
    author_id: Optional[uuid.UUID],
    tag: Optional[str],
    limit: int,
    offset: int,
) -> Tuple[int, List[Story]]:
    q = db.query(Story).filter(Story.deleted_at.is_(None))

    if status_filter is not None:
        # ✅ compare with Enum; works for SQLAlchemy Enum columns
        q = q.filter(Story.status == status_filter)

    if author_id:
        q =  q.filter(Story.user_id == author_id)

    if tag:
        q = q.join(Story.tags).filter(Tag.name == tag)

    total = q.count()
    items = q.order_by(Story.created_at.desc()).limit(limit).offset(offset).all()
    return total, items

def moderate_content(texts: List[str]) -> Tuple[bool, List[str]]:
    """Scans text for profanity. Returns (is_flagged, categories)."""
    for text in texts:
        if profanity.contains_profanity(text or ""):
            return True, ["profanity"]
    return False, []
