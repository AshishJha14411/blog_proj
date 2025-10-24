from typing import Optional, List
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
import uuid # Import for type hinting

from app.schemas.comments import CommentCreate, CommentOut, CommentList
from app.schemas.user import UserOut # Assuming UserOut has been updated for UUIDs
from app.services.comments import create_comment, list_comments, delete_comment
from app.dependencies import get_db, get_current_user, get_current_user_optional

router = APIRouter(tags=["Comments"])

@router.post("/stories/{story_id}/comments", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
def post_comment(
    story_id: uuid.UUID, # <-- FIX: Changed from str to uuid.UUID
    data: CommentCreate, 
    db: Session = Depends(get_db), 
    current_user = Depends(get_current_user)
):
    new_comment = create_comment(db, story_id, data.content, current_user)
    
    # --- FIX: Manually build the response to handle UUID -> str conversion ---
    return CommentOut(
        id=str(new_comment.id),
        user_id=str(new_comment.user_id),
        post_id=str(new_comment.story_id), # Use the correct attribute name
        content=new_comment.content,
        created_at=new_comment.created_at,
        user=UserOut.model_validate(new_comment.user,from_attributes=True) # Assuming UserOut is correctly configured
    )


@router.get("/stories/{story_id}/comments", response_model=CommentList, status_code=status.HTTP_200_OK)
def get_story_comments(
    story_id: uuid.UUID, # <-- FIX: Changed from str to uuid.UUID
    limit: int = Query(10, gt=0, le=100), 
    offset: int = Query(0, ge=0), 
    db: Session = Depends(get_db)
):
    total, items = list_comments(db, story_id, limit, offset)
    
    # --- FIX: Apply the same manual conversion pattern here for lists ---
    validated_items = [
        CommentOut(
            id=str(comment.id),
            user_id=str(comment.user_id),
            post_id=str(comment.story_id),
            content=comment.content,
            created_at=comment.created_at,
            user=UserOut(id=str(comment.user.id), username=comment.user.username, email=comment.user.email)
        ) for comment in items
    ]
    return CommentList(total=total, items=validated_items)

@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_comment(
    comment_id: uuid.UUID, # <-- FIX: Changed from str to uuid.UUID
    db: Session = Depends(get_db), 
    current_user = Depends(get_current_user)
):
    delete_comment(db, comment_id, current_user)
