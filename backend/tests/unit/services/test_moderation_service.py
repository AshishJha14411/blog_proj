# import pytest
# from fastapi import HTTPException, status
# from sqlalchemy.orm import Session
# import uuid

# # Import the services we are testing
# from app.services.moderation import (
#     flag_story, 
#     flag_comment, 
#     resolve_flag, 
#     approve_story, 
#     reject_story,
#     moderate_content
# )

# # Import factories
# from tests.factories import (
#     UserFactory, 
#     StoryFactory, 
#     CommentFactory, 
#     FlagFactory, 
#     RoleFactory
# )

# # Import models
# from app.models.flag import Flag
# from app.models.stories import Story, StoryStatus


# def test_flag_story_success(db_session: Session):
#     """
#     GIVEN a user and a story
#     WHEN the user flags the story
#     THEN a new Flag row is created with 'open' status
#     """
#     # ARRANGE
#     user = UserFactory()
#     story = StoryFactory()
    
#     # ACT
#     flag = flag_story(
#         db=db_session,
#         story_id=story.id,
#         reason="This is offensive",
#         current_user=user
#     )

#     # ASSERT
#     assert isinstance(flag, Flag)
#     assert flag.reason == "This is offensive"
#     assert flag.status == "open"
#     assert flag.flagged_by_user_id == user.id
#     assert flag.story_id == story.id
    
#     # Check database
#     db_flag = db_session.get(Flag, flag.id)
#     assert db_flag is not None
#     assert db_flag.reason == "This is offensive"


# def test_approve_story(db_session: Session):
#     """
#     GIVEN a story that is pending ('is_published'=False) and has an open flag
#     WHEN a moderator approves the story
#     THEN the story should be set to 'published' and the flag closed
#     """
#     # ARRANGE
#     # Create a moderator
#     mod_role = RoleFactory(name="moderator")
#     moderator = UserFactory(role=mod_role)
    
#     # Create a story that is pending and flagged
#     story = StoryFactory(is_published=False, is_flagged=True, status=StoryStatus.draft)
#     flag = FlagFactory(story=story, status="open")
    
#     # ACT
#     approved_story = approve_story(
#         db=db_session,
#         story_id=story.id,
#         moderator=moderator,
#         note="All good."
#     )
    
#     # ASSERT - Story is updated
#     assert approved_story.is_published is True
#     assert approved_story.is_flagged is False
#     assert approved_story.status == StoryStatus.published
    
#     # ASSERT - Flag is closed
#     db_session.refresh(flag) # Refresh the flag object from the DB
#     assert flag.status == "approved"
#     assert flag.resolved_by_id == moderator.id
#     assert "Moderator Note: All good." in flag.reason


# def test_reject_story(db_session: Session):
#     """
#     GIVEN a published story
#     WHEN a moderator rejects it
#     THEN the story should be set to 'rejected' and unpublished
#     """
#     # ARRANGE
#     mod_role = RoleFactory(name="moderator")
#     moderator = UserFactory(role=mod_role)
    
#     story = StoryFactory(is_published=True, status=StoryStatus.published)

#     # ACT
#     rejected_story = reject_story(
#         db=db_session,
#         story_id=story.id,
#         moderator=moderator,
#         reason="Violates guidelines"
#     )

#     # ASSERT
#     assert rejected_story.is_published is False
#     assert rejected_story.is_flagged is True # Rejected stories are flagged
#     assert rejected_story.status == StoryStatus.rejected


# def test_moderate_content_pure_function():
#     """
#     GIVEN the moderate_content function (which has no DB)
#     WHEN it's passed clean and profane text
#     THEN it should return the correct flag
#     """
#     # ARRANGE
#     clean_text = ["This", "is", "a", "lovely", "story"]
#     profane_text = ["This", "is", "a", "hell", "of a story"] # 'hell' is a default bad word
    
#     # ACT
#     is_flagged_clean, _ = moderate_content(clean_text)
#     is_flagged_profane, _ = moderate_content(profane_text)
    
#     # ASSERT
#     assert is_flagged_clean is False
#     assert is_flagged_profane is True