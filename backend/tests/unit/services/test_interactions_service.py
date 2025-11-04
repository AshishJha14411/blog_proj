# import pytest
# from fastapi import HTTPException, status
# from sqlalchemy.orm import Session
# import uuid

# # Import the services we are testing
# from app.services.interactions import toggle_like, toggle_bookmark, list_bookmarks

# # Import factories
# from tests.factories import UserFactory, StoryFactory, LikeFactory, BookmarkFactory

# # Import models
# from app.models.like import Like
# from app.models.bookmarks import Bookmark


# def test_toggle_like_new_like(db_session: Session):
#     """
#     GIVEN a user and a story (not liked)
#     WHEN the user calls toggle_like
#     THEN the function should return True and a new Like row is created
#     """
#     # ARRANGE
#     user = UserFactory()
#     story = StoryFactory()
    
#     # ACT
#     # We ignore the notification service for now
#     # This is a unit test, so we can mock 'notify' later if needed
#     result = toggle_like(db=db_session, story_id=story.id, current_user=user)

#     # ASSERT
#     assert result is True
    
#     # Check the database
#     like = db_session.query(Like).filter_by(user_id=user.id, story_id=story.id).one_or_none()
#     assert like is not None
#     assert like.story_id == story.id


# def test_toggle_like_unlike(db_session: Session):
#     """
#     GIVEN a user who has already liked a story
#     WHEN the user calls toggle_like again
#     THEN the function should return False and the Like row is deleted
#     """
#     # ARRANGE
#     user = UserFactory()
#     story = StoryFactory()
#     # Use the factory to create a pre-existing like
#     like = LikeFactory(user=user, story=story)
    
#     # Ensure it's in the DB
#     assert db_session.query(Like).count() == 1

#     # ACT
#     result = toggle_like(db=db_session, story_id=story.id, current_user=user)

#     # ASSERT
#     assert result is False
    
#     # Check the database
#     assert db_session.query(Like).count() == 0


# def test_list_bookmarks(db_session: Session):
#     """
#     GIVEN a user with 2 bookmarks and other stories in the DB
#     WHEN list_bookmarks is called
#     THEN it should return ONLY the 2 bookmarked stories
#     """
#     # ARRANGE
#     user = UserFactory()
    
#     # Create 2 stories and bookmark them
#     story1 = StoryFactory()
#     story2 = StoryFactory()
#     BookmarkFactory(user=user, story=story1)
#     BookmarkFactory(user=user, story=story2)
    
#     # Create a 3rd story that is NOT bookmarked
#     StoryFactory()
    
#     # ACT
#     bookmarked_stories = list_bookmarks(db=db_session, current_user=user)

#     # ASSERT
#     assert len(bookmarked_stories) == 2
    
#     # Check that the correct stories were returned
#     bookmarked_ids = {str(s.id) for s in bookmarked_stories}
#     assert str(story1.id) in bookmarked_ids
#     assert str(story2.id) in bookmarked_ids