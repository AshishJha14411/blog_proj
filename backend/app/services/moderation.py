from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import datetime
from typing import List, Tuple, Optional
import uuid

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

def resolve_flag(db: Session, flag_id: uuid.UUID, status_str: str, current_user: User) -> Flag:
    flag = db.get(Flag, flag_id)
    if not flag:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Flag not found")
    
    if status_str not in {"resolved", "ignored"}:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid status. Must be 'resolved' or 'ignored'.")
        
    flag.status = status_str
    flag.resolved_by_id = current_user.id
    flag.resolved_at = datetime.utcnow()
    db.commit()
    db.refresh(flag)
    return flag


# --- Content Moderation Logic ---

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

def moderation_queue(db: Session, status_filter: Optional[str], author_id: Optional[uuid.UUID], tag: Optional[str], limit: int, offset: int) -> Tuple[int, List[Story]]:
    q = db.query(Story).filter(Story.deleted_at == None)
    if status_filter:
        q = q.filter(Story.status == status_filter)
    else:
        q = q.filter(Story.is_flagged == True)
    if author_id:
        q = q.filter(Story.user_id == author_id)
    if tag:
        from app.models.tags import Tag
        q = q.join(Story.tags).filter(Tag.name == tag)
    
    total = q.count()
    items = q.order_by(Story.created_at.desc()).offset(offset).limit(limit).all()
    return total, items

def moderate_content(texts: List[str]) -> Tuple[bool, List[str]]:
    """Scans text for profanity. Returns (is_flagged, categories)."""
    for text in texts:
        if profanity.contains_profanity(text or ""):
            return True, ["profanity"]
    return False, []
