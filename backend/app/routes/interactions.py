from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
import uuid # Import uuid for type hinting
from typing import List

from app.schemas.interaction import ToggleResponse, BookmarkList
from app.schemas.stories import StoryOut, UserSummary, TagSummary # Import for explicit response
from app.services.interactions import toggle_like, toggle_bookmark, list_bookmarks
from app.dependencies import get_db, get_current_user

router = APIRouter(tags=["Interactions"])

@router.post("/stories/{story_id}/like", response_model=ToggleResponse, status_code=status.HTTP_200_OK)
def like_story(
    story_id: uuid.UUID, # <-- FIX: Changed from post_id: int
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    liked = toggle_like(db, story_id, current_user)
    return ToggleResponse(success=True, liked=liked)

@router.post("/stories/{story_id}/bookmark", response_model=ToggleResponse, status_code=status.HTTP_200_OK)
def bookmark_story(
    story_id: uuid.UUID, # <-- FIX: Changed from post_id: int
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    bookmarked = toggle_bookmark(db, story_id, current_user)
    return ToggleResponse(success=True, bookmarked=bookmarked)

@router.get("/users/me/bookmarks", response_model=BookmarkList, status_code=status.HTTP_200_OK)
def get_my_bookmarks(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    bookmarked_stories = list_bookmarks(db, current_user)
    
    # Apply the same explicit conversion pattern to fix the UUID -> str issue
    validated_items = [
        StoryOut(
            id=str(story.id),
            title=story.title,
            content=story.content,
            user_id=str(story.user_id),
            created_at=story.created_at,
            updated_at=story.updated_at,
            header=story.header,
            cover_image_url=story.cover_image_url,
            is_published=story.is_published,
            source=story.source,
              user=UserSummary(
            id=str(story.user.id),
            username=story.user.username
        ),
            tags=[TagSummary.from_orm(tag) for tag in story.tags]
        ) for story in bookmarked_stories
    ]
    
    return BookmarkList(items=validated_items)
