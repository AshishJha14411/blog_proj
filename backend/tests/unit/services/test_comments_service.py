# tests/unit/services/test_comment_service.py

import uuid
import pytest
from sqlalchemy.orm import Session
from fastapi import HTTPException

import app.services.comments as comment_service
from app.models.comment import Comment
from app.models.view_history import ViewHistory  # not used here, but keeps test imports parallel
from tests.factories import (
    UserFactory,
    RoleFactory,
    StoryFactory,
)

# -----------------------
# Helpers
# -----------------------

class NotifySink:
    def __init__(self):
        self.calls = []
    def __call__(self, db, *, recipient_id, action, actor_id, target_type, target_id):
        # capture the arguments we care about for assertions
        self.calls.append({
            "recipient_id": recipient_id,
            "action": action,
            "actor_id": actor_id,
            "target_type": target_type,
            "target_id": target_id,
        })

# -----------------------
# create_comment
# -----------------------

def test_create_comment_sends_notify_to_author_when_commenter_diff_user(db_session: Session, monkeypatch):
    author = UserFactory(role=RoleFactory(name="creator"))
    story = StoryFactory(user=author)  # Story belongs to the author
    commenter = UserFactory(role=RoleFactory(name="user"))

    sink = NotifySink()
    # comment_service imported notify at module level; patch it here
    monkeypatch.setattr(comment_service, "notify", sink)

    comment = comment_service.create_comment(
        db_session, story_id=story.id, content="Nice post!", current_user=commenter
    )

    # DB persisted + correct FKs
    assert isinstance(comment, Comment)
    assert comment.user_id == commenter.id
    assert comment.story_id == story.id
    assert db_session.query(Comment).count() == 1

    # Notification fired to story author (not the commenter)
    assert len(sink.calls) == 1
    call = sink.calls[0]
    assert call["recipient_id"] == author.id
    assert call["actor_id"] == commenter.id
    assert call["action"] == "commented"
    assert call["target_type"] == "story"
    assert call["target_id"] == story.id


def test_create_comment_does_not_notify_when_author_comments_own_story(db_session: Session, monkeypatch):
    author = UserFactory(role=RoleFactory(name="creator"))
    story = StoryFactory(user=author)

    sink = NotifySink()
    monkeypatch.setattr(comment_service, "notify", sink)

    comment = comment_service.create_comment(
        db_session, story_id=story.id, content="self comment", current_user=author
    )
    assert db_session.query(Comment).count() == 1
    assert len(sink.calls) == 0  # no notify to self


def test_create_comment_404_story_not_found(db_session: Session, monkeypatch):
    user = UserFactory()
    missing_id = uuid.uuid4()
    with pytest.raises(HTTPException) as exc:
        comment_service.create_comment(db_session, story_id=missing_id, content="hi", current_user=user)
    assert exc.value.status_code == 404

# -----------------------
# list_comments
# -----------------------

def test_list_comments_returns_desc_order_and_paginates(db_session: Session):
    author = UserFactory()
    story = StoryFactory(user=author)
    u1 = UserFactory()
    u2 = UserFactory()

    # Create 3 comments in sequence
    c1 = comment_service.create_comment(db_session, story.id, "first", u1)
    c2 = comment_service.create_comment(db_session, story.id, "second", u2)
    c3 = comment_service.create_comment(db_session, story.id, "third", u1)

    # Expect desc by created_at -> c3, c2, c1
    total, page1 = comment_service.list_comments(db_session, story_id=story.id, limit=2, offset=0)
    assert total == 3
    assert [c.content for c in page1] == ["third", "second"]

    _, page2 = comment_service.list_comments(db_session, story_id=story.id, limit=2, offset=2)
    assert [c.content for c in page2] == ["first"]

# -----------------------
# delete_comment
# -----------------------

def test_delete_comment_by_owner_succeeds(db_session: Session):
    owner = UserFactory()
    story = StoryFactory(user=owner)
    c = comment_service.create_comment(db_session, story.id, "mine", owner)

    comment_service.delete_comment(db_session, comment_id=c.id, current_user=owner)
    assert db_session.query(Comment).count() == 0


def test_delete_comment_by_moderator_succeeds(db_session: Session):
    owner = UserFactory()
    story = StoryFactory(user=owner)
    c = comment_service.create_comment(db_session, story.id, "reported", owner)

    moderator = UserFactory(role=RoleFactory(name="moderator"))
    comment_service.delete_comment(db_session, comment_id=c.id, current_user=moderator)
    assert db_session.query(Comment).count() == 0


def test_delete_comment_forbidden_for_other_user(db_session: Session):
    owner = UserFactory()
    story = StoryFactory(user=owner)
    c = comment_service.create_comment(db_session, story.id, "cant-touch-this", owner)

    stranger = UserFactory(role=RoleFactory(name="user"))
    with pytest.raises(HTTPException) as exc:
        comment_service.delete_comment(db_session, comment_id=c.id, current_user=stranger)
    assert exc.value.status_code == 403
    assert db_session.query(Comment).count() == 1  # still there


def test_delete_comment_404_when_missing(db_session: Session):
    user = UserFactory()
    missing_id = uuid.uuid4()
    with pytest.raises(HTTPException) as exc:
        comment_service.delete_comment(db_session, comment_id=missing_id, current_user=user)
    assert exc.value.status_code == 404
