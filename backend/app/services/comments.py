from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import datetime
from typing import Tuple, List
import uuid # Import for type hinting
from app.services.notifications import notify
from app.models.comment import Comment
from app.models.stories import Story
from app.models.user import User

def create_comment(db: Session, story_id: uuid.UUID, content: str, current_user: User) -> Comment:
    # --- FIX: Ensure we are querying with a UUID object ---
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Story not found")
    
    # --- FIX: Pass the raw UUID objects to the model constructor ---
    comment = Comment(
        user_id=current_user.id, 
        story_id=story_id, 
        content=content
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    if story.user_id and story.user_id != current_user.id:
        notify(
            db,
            recipient_id=story.user_id,
            action="commented",
            actor_id=current_user.id,
            target_type="story",
            target_id=story.id,
        )

    return comment


def list_comments(db: Session, story_id: uuid.UUID, limit: int, offset: int) -> Tuple[int, List[Comment]]:
    # --- FIX: Ensure we are querying with a UUID object ---
    query = db.query(Comment).filter(Comment.story_id == story_id).order_by(Comment.created_at.desc())
    total = query.count()
    items = query.offset(offset).limit(limit).all()
    return total, items


def delete_comment(db: Session, comment_id: uuid.UUID, current_user: User) -> None:
    # --- FIX: Ensure we are querying with a UUID object ---
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Comment not Found")
    
    # Proactive fix: typo `anme` -> `name`
    if (comment.user_id != current_user.id and current_user.role.name not in ("moderator", "superadmin")):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not authorized")
        
    db.delete(comment)
    db.commit()
