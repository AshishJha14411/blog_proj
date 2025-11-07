# tests/unit/services/test_interactions_service.py

import uuid
import pytest
from sqlalchemy.orm import Session
from fastapi import HTTPException

import app.services.interactions as interactions_service
from app.models.like import Like
from app.models.bookmarks import Bookmark
from app.models.stories import Story
from tests.factories import UserFactory, RoleFactory, StoryFactory

# Simple sink to capture notify() calls
class NotifySink:
    def __init__(self):
        self.calls = []
    def __call__(self, db, *, recipient_id, action, actor_id, target_type, target_id):
        self.calls.append({
            "recipient_id": recipient_id,
            "action": action,
            "actor_id": actor_id,
            "target_type": target_type,
            "target_id": target_id,
        })

# -----------------------
# toggle_like
# -----------------------

def test_toggle_like_404_when_story_missing(db_session: Session):
    user = UserFactory(role=RoleFactory(name="user"))
    with pytest.raises(HTTPException) as exc:
        interactions_service.toggle_like(db_session, uuid.uuid4(), user)
    assert exc.value.status_code == 404

def test_toggle_like_adds_then_removes_like_and_notifies_other_author(db_session: Session, monkeypatch):
    author = UserFactory(role=RoleFactory(name="creator"))
    story = StoryFactory(user=author)
    liker = UserFactory(role=RoleFactory(name="user"))

    sink = NotifySink()
    monkeypatch.setattr(interactions_service, "notify", sink)

    # First call -> like added, True returned
    r1 = interactions_service.toggle_like(db_session, story.id, liker)
    assert r1 is True
    assert db_session.query(Like).filter_by(user_id=liker.id, story_id=story.id).count() == 1

    # Notification to author (not self)
    assert len(sink.calls) == 1
    n = sink.calls[0]
    assert n["recipient_id"] == author.id
    assert n["actor_id"] == liker.id
    assert n["action"] == "liked"
    assert n["target_type"] == "story"
    assert n["target_id"] == story.id

    # Second call -> like removed, False returned
    r2 = interactions_service.toggle_like(db_session, story.id, liker)
    assert r2 is False
    assert db_session.query(Like).filter_by(user_id=liker.id, story_id=story.id).count() == 0

def test_toggle_like_self_like_no_notify(db_session: Session, monkeypatch):
    author = UserFactory(role=RoleFactory(name="creator"))
    story = StoryFactory(user=author)

    sink = NotifySink()
    monkeypatch.setattr(interactions_service, "notify", sink)

    r = interactions_service.toggle_like(db_session, story.id, author)
    assert r is True
    assert db_session.query(Like).filter_by(user_id=author.id, story_id=story.id).count() == 1
    assert len(sink.calls) == 0  # no notify to self

# -----------------------
# toggle_bookmark
# -----------------------

def test_toggle_bookmark_404_when_story_missing(db_session: Session):
    user = UserFactory(role=RoleFactory(name="user"))
    with pytest.raises(HTTPException) as exc:
        interactions_service.toggle_bookmark(db_session, uuid.uuid4(), user)
    assert exc.value.status_code == 404

def test_toggle_bookmark_adds_then_removes_and_notifies_other_author(db_session: Session, monkeypatch):
    author = UserFactory(role=RoleFactory(name="creator"))
    story = StoryFactory(user=author)
    keeper = UserFactory(role=RoleFactory(name="user"))

    sink = NotifySink()
    monkeypatch.setattr(interactions_service, "notify", sink)

    # First call -> bookmark added, True
    r1 = interactions_service.toggle_bookmark(db_session, story.id, keeper)
    assert r1 is True
    assert db_session.query(Bookmark).filter_by(user_id=keeper.id, story_id=story.id).count() == 1

    # Notification fired to author (note: service currently uses action="liked" for bookmarks too)
    assert len(sink.calls) == 1
    n = sink.calls[0]
    assert n["recipient_id"] == author.id
    assert n["actor_id"] == keeper.id
    assert n["action"] == "liked"          # mirrors current implementation
    assert n["target_type"] == "story"
    assert n["target_id"] == story.id

    # Second call -> bookmark removed, False
    r2 = interactions_service.toggle_bookmark(db_session, story.id, keeper)
    assert r2 is False
    assert db_session.query(Bookmark).filter_by(user_id=keeper.id, story_id=story.id).count() == 0

def test_toggle_bookmark_self_no_notify(db_session: Session, monkeypatch):
    author = UserFactory(role=RoleFactory(name="creator"))
    story = StoryFactory(user=author)

    sink = NotifySink()
    monkeypatch.setattr(interactions_service, "notify", sink)

    r = interactions_service.toggle_bookmark(db_session, story.id, author)
    assert r is True
    assert db_session.query(Bookmark).filter_by(user_id=author.id, story_id=story.id).count() == 1
    assert len(sink.calls) == 0

# -----------------------
# list_bookmarks
# -----------------------

def test_list_bookmarks_returns_only_current_user_and_in_desc_order(db_session: Session):
    user = UserFactory(role=RoleFactory(name="user"))
    other = UserFactory(role=RoleFactory(name="user"))
    s1 = StoryFactory(user=UserFactory())  # arbitrary authors
    s2 = StoryFactory(user=UserFactory())
    s3 = StoryFactory(user=UserFactory())

    # create bookmarks in sequence to get increasing created_at
    b1 = Bookmark(user_id=user.id, story_id=s1.id)
    db_session.add(b1); db_session.commit()
    b2 = Bookmark(user_id=user.id, story_id=s2.id)
    db_session.add(b2); db_session.commit()
    b3 = Bookmark(user_id=other.id, story_id=s3.id)   # belongs to someone else
    db_session.add(b3); db_session.commit()

    stories = interactions_service.list_bookmarks(db_session, user)
    ids = [s.id for s in stories]

    # should exclude other's bookmark and be ordered newest-first (b2, then b1)
    assert ids == [s2.id, s1.id]
