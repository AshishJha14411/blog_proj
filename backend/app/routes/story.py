from fastapi import APIRouter, Depends, status, Query, Request
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid

# Import all dependencies and the unified schemas/services
from app.dependencies import get_db, require_roles, get_current_user_optional, get_current_user
from app.models.user import User
from app.schemas.stories import StoryCreate, StoryUpdate, StoryOut, StoryList, UserSummary, TagSummary, StoryGenerateIn, StoryFeedbackIn
from app.services import story

# --- UNIFIED ROUTER ---
router = APIRouter(prefix="/stories", tags=["Stories"])


# --- HUMAN-WRITTEN STORY ENDPOINTS ---

@router.post("/", response_model=StoryOut, status_code=status.HTTP_201_CREATED)
def create_new_story(
    data: StoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("creator", "moderator", "superadmin"))
):
    """Creates a new story written by a user."""
    new_story = story.create_story(db, data, current_user)
    
    # Manually build the response to ensure all fields and types are correct
    print(f"this is the tag {new_story.tags}")
    return StoryOut(
        id=str(new_story.id),
        title=new_story.title,
        content=new_story.content,
        user_id=str(new_story.user_id),
        created_at=new_story.created_at,
        updated_at=new_story.updated_at,
        header=new_story.header,
        cover_image_url=new_story.cover_image_url,
        is_published=new_story.is_published,
        source=new_story.source,
        # user=UserSummary.from_orm(new_story.user),
        tags=[
            TagSummary(id=str(tag.id), name=tag.name) for tag in new_story.tags
        ],
        
        
        user=UserSummary(
            id=str(new_story.user.id),
            username=new_story.user.username
        ),
    )

@router.get("/", response_model=StoryList, status_code=status.HTTP_200_OK)
def list_all_stories(
    limit: int = Query(10, gt=0, le=100),
    offset: int = Query(0, ge=0),
    tag: Optional[str] = Query(None),
    author_id: Optional[uuid.UUID] = Query(None), # Correctly a UUID
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Lists all stories, with filters."""
    total, items = story.get_all_stories(db, limit, offset, tag, author_id, current_user)
    
    # Manually validate each item to populate computed fields like is_liked_by_user
    # validated_items = [
    #     StoryOut(
    #         id=str(story.id),
    #         title=story.title,
    #         content=story.content,
    #         user_id=str(story.user_id),
    #         created_at=story.created_at,
    #         updated_at=story.updated_at,
    #         header=story.header,
    #         cover_image_url=story.cover_image_url,
    #         is_published=story.is_published,
    #         source=story.source,
    #         user=UserSummary(id=str(story.user.id), username=story.user.username),
    #         tags=[TagSummary(id=str(tag.id), name=tag.name) for tag in story.tags],
    #         is_liked_by_user=getattr(story, 'is_liked_by_user', False),
    #         is_bookmarked_by_user=getattr(story, 'is_bookmarked_by_user', False)
    #     ) for story in items
    # ]
    validated_items = [StoryOut.model_validate(item,from_attributes=True) for item in items]
    return StoryList(total=total, limit=limit, offset=offset, items=validated_items)

@router.get("/me", response_model=StoryList, status_code=status.HTTP_200_OK)
def list_my_stories(
    limit: int = Query(10, gt=0, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lists all stories created by the current authenticated user."""
    total, items = story.get_user_stories(db, current_user, limit, offset)
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
            user=UserSummary(id=str(story.user.id), username=story.user.username),
            tags=[TagSummary(id=str(tag.id), name=tag.name) for tag in story.tags],
            is_liked_by_user=getattr(story, 'is_liked_by_user', False),
            is_bookmarked_by_user=getattr(story, 'is_bookmarked_by_user', False)
        ) for story in items
    ]
    return StoryList(total=total, limit=limit, offset=offset, items=validated_items)


@router.get("/{story_id}", response_model=StoryOut, status_code=status.HTTP_200_OK)
def read_story_details(
    story_id: uuid.UUID, # Correctly a UUID
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Gets the full details of a single story."""
    story_object = story.get_story_details(db, story_id, current_user, request)
    print(f"sthis story {story_object}")
    return StoryOut(
        id=str(story_object.id),
        title=story_object.title,
        content=story_object.content,
        user_id=str(story_object.user_id),
        created_at=story_object.created_at,
        updated_at=story_object.updated_at,
        header=story_object.header,
        cover_image_url=story_object.cover_image_url,
        is_published=story_object.is_published,
        source=story_object.source,
        
        # Explicitly build the nested UserSummary
        user=UserSummary(
            id=str(story_object.user.id),
            username=story_object.user.username
        ),
        
        # Explicitly build the list of TagSummary objects, converting their IDs
        tags=[TagSummary(id=str(tag.id), name=tag.name) for tag in story_object.tags],

        # Pass through the dynamically computed fields from the service
        is_liked_by_user=story_object.is_liked_by_user,
        is_bookmarked_by_user=story_object.is_bookmarked_by_user
    )


@router.patch("/{story_id}", response_model=StoryOut, status_code=status.HTTP_200_OK)
def update_existing_story(
    story_id: uuid.UUID, # Correctly a UUID
    data: StoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Updates a story owned by the current user."""
    updated_story = story.update_story(db, story_id, data, current_user)
    return StoryOut(
        id=str(updated_story.id),
        title=updated_story.title,
        content=updated_story.content,
        user_id=str(updated_story.user_id),
        created_at=updated_story.created_at,
        updated_at=updated_story.updated_at,
        header=updated_story.header,
        cover_image_url=updated_story.cover_image_url,
        is_published=updated_story.is_published,
        source=updated_story.source,
        # user=UserSummary.from_orm(new_story.user),
        tags=[
            TagSummary(id=str(tag.id), name=tag.name) for tag in updated_story.tags
        ],
        
        
        user=UserSummary(
            id=str(updated_story.user.id),
            username=updated_story.user.username
        ),
    )


@router.delete("/{story_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_existing_story(
    story_id: uuid.UUID, # Correctly a UUID
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Deletes a story owned by the current user."""
    story.delete_story(db, story_id, current_user)
    return None


# --- AI STORY GENERATION ENDPOINTS ---

@router.post("/generate", response_model=StoryOut, status_code=status.HTTP_201_CREATED)
def generate_ai_story(
    data: StoryGenerateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("creator", "moderator", "superadmin")),
):
    """Generates a new story using an AI model."""
    new_story = story.generate_story(db, data, current_user)
    return StoryOut(
        id=str(new_story.id),
        user_id=str(new_story.user_id),
        title=new_story.title,
        content=new_story.content,
        created_at=new_story.created_at,
        updated_at=new_story.updated_at,
        header=new_story.header,
        cover_image_url=new_story.cover_image_url,
        is_published=new_story.is_published,
        source=new_story.source,
        user=UserSummary(id=str(new_story.user.id), username=new_story.user.username),
        tags=[TagSummary.from_orm(tag) for tag in new_story.tags]
    )


@router.post("/{story_id}/feedback", response_model=StoryOut, status_code=status.HTTP_200_OK)
def apply_feedback_to_story(
    story_id: uuid.UUID, # Correctly a UUID
    data: StoryFeedbackIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Regenerates an AI story with new feedback."""
    regenerated_story = story.regenerate_with_feedback(db, story_id, data.feedback, current_user)
    return StoryOut(
        id=str(regenerated_story.id),
        user_id=str(regenerated_story.user_id),
        title=regenerated_story.title,
        content=regenerated_story.content,
        created_at=regenerated_story.created_at,
        updated_at=regenerated_story.updated_at,
        header=regenerated_story.header,
        cover_image_url=regenerated_story.cover_image_url,
        is_published=regenerated_story.is_published,
        source=regenerated_story.source,
        user=UserSummary(id=str(regenerated_story.user.id), username=regenerated_story.user.username),
        tags=[TagSummary.from_orm(tag) for tag in regenerated_story.tags]
    )


@router.post("/{story_id}/publish", response_model=StoryOut, status_code=status.HTTP_200_OK)
def publish_a_story(
    story_id: uuid.UUID, # Correctly a UUID
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Publishes a story, making it visible to all users."""
    published_story = story.publish_story(db, story_id, current_user)
    return StoryOut(
        id=str(published_story.id),
        title=published_story.title,
        content=published_story.content,
        user_id=str(published_story.user_id),
        created_at=published_story.created_at,
        updated_at=published_story.updated_at,
        header=published_story.header,
        cover_image_url=published_story.cover_image_url,
        is_published=published_story.is_published,
        source=published_story.source,
        # user=UserSummary.from_orm(new_story.user),
        tags=[
            TagSummary(id=str(tag.id), name=tag.name) for tag in published_story.tags
        ],
        
        
        user=UserSummary(
            id=str(published_story.user.id),
            username=published_story.user.username
        ),
    )


@router.post("/{story_id}/unpublish", response_model=StoryOut, status_code=status.HTTP_200_OK)
def unpublish_a_story(
    story_id: uuid.UUID, # Correctly a UUID
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Unpublishes a story, hiding it from public view."""
    unpublished_story = story.unpublish_story(db, story_id, current_user)
    return StoryOut.model_validate(unpublished_story, from_attributes=True)

