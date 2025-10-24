from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import uuid # Import uuid for type hinting
from typing import List
from app.models.like import Like
from app.models.bookmarks import Bookmark
from app.models.stories import Story
from app.models.user import User
from app.services.notifications import notify
def toggle_like(db: Session, story_id: uuid.UUID, current_user: User) -> bool:
    story = db.query(Story).get(story_id)
    if not story:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Story not found")
    
    # Use the correct column name 'story_id'
    existing = db.query(Like).filter_by(user_id=current_user.id, story_id=story_id).first()
    
    if existing:
        db.delete(existing)
        db.commit()
        return False
    else:
        like = Like(user_id=current_user.id, story_id=story_id)
        db.add(like)
        db.commit()
        if story.user_id and story.user_id != current_user.id:
            notify(
                db,
                recipient_id=story.user_id,
                action="liked",
                actor_id=current_user.id,
                target_type="story",
                target_id=story.id,
            )
        return True

def toggle_bookmark(db: Session, story_id: uuid.UUID, current_user: User) -> bool:
    story = db.query(Story).get(story_id)
    if not story:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Story not found")
    
    # Use the correct column name 'story_id'
    existing = db.query(Bookmark).filter_by(user_id=current_user.id, story_id=story_id).first()
    
    if existing:
        db.delete(existing)
        db.commit()
        return False
    else:
        bookmark = Bookmark(user_id=current_user.id, story_id=story_id)
        db.add(bookmark)
        db.commit()
        if story.user_id and story.user_id != current_user.id:
            notify(
                db,
                recipient_id=story.user_id,
                action="liked",
                actor_id=current_user.id,
                target_type="story",
                target_id=story.id,
            )
        return True

def list_bookmarks(db: Session, current_user: User) -> List[Story]:
    # A more efficient query to get all bookmarked stories for the user
    stories = (
        db.query(Story)
          .join(Bookmark, Story.id == Bookmark.story_id)
          .filter(Bookmark.user_id == current_user.id)
          .order_by(Bookmark.created_at.desc())
          .all()
    )
    return stories
