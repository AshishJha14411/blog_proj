# # app/routes/stories.py
# from fastapi import APIRouter, Depends, status
# from sqlalchemy.orm import Session

# from app.dependencies import get_db, get_current_user
# from app.schemas.stories import StoryGenerateIn, StoryFeedbackIn
# from app.schemas.stories import PostOut
# from app.services.stories import (
#     generate_story,
#     regenerate_with_feedback,
#     publish_story,
#     unpublish_story,
# )

# router = APIRouter(prefix="/stories", tags=["Stories"])

# @router.post("/generate", response_model=PostOut, status_code=status.HTTP_201_CREATED)
# def create_story(
#     data: StoryGenerateIn,
#     db: Session = Depends(get_db),
#     current_user = Depends(get_current_user),
# ):
#     return generate_story(db, data, current_user)

# @router.post("/{post_id}/feedback", response_model=PostOut, status_code=status.HTTP_200_OK)
# def apply_feedback(
#     post_id: int,
#     data: StoryFeedbackIn,
#     db: Session = Depends(get_db),
#     current_user = Depends(get_current_user),
# ):
#     return regenerate_with_feedback(db, post_id, data.feedback, current_user)

# @router.post("/{post_id}/publish", response_model=PostOut, status_code=status.HTTP_200_OK)
# def publish(
#     post_id: int,
#     db: Session = Depends(get_db),
#     current_user = Depends(get_current_user),
# ):
#     return publish_story(db, post_id, current_user)

# @router.post("/{post_id}/unpublish", response_model=PostOut, status_code=status.HTTP_200_OK)
# def unpublish(
#     post_id: int,
#     db: Session = Depends(get_db),
#     current_user = Depends(get_current_user),
# ):
#     return unpublish_story(db, post_id, current_user)
