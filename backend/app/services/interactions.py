from sqlalchemy.orm import Session, joinedload, selectinload
from fastapi import HTTPException, status
import uuid  # Import uuid for type hinting
from typing import Tuple, List
from app.models.like import Like
from app.models.bookmarks import Bookmark
from app.models.stories import Story
from app.models.user import User
from app.services.notifications import notify


def _get_active_story(db: Session, story_id: uuid.UUID) -> Story:
    story = (
        db.query(Story)
        .filter(Story.id == story_id, Story.deleted_at.is_(None))
        .first()
    )
    if not story:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Story not found")
    return story


def toggle_like(db: Session, story_id: uuid.UUID, current_user: User) -> bool:
    story = _get_active_story(db, story_id)

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
    story = _get_active_story(db, story_id)

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
            # G20: notify action was "liked" (copy-paste bug) — should be "bookmarked".
            notify(
                db,
                recipient_id=story.user_id,
                action="bookmarked",
                actor_id=current_user.id,
                target_type="story",
                target_id=story.id,
            )
        return True


def list_bookmarks(
    db: Session,
    current_user: User,
    limit: int = 10,
    offset: int = 0,
) -> Tuple[int, List[Story]]:
    query = (
        db.query(Story)
        .join(Bookmark, Story.id == Bookmark.story_id)
        .filter(
            Bookmark.user_id == current_user.id,
            Story.deleted_at.is_(None),
        )
        .options(joinedload(Story.user), selectinload(Story.tags))
        .order_by(Bookmark.created_at.desc())
    )
    total = query.count()
    items = query.offset(offset).limit(limit).all()
    return total, items
