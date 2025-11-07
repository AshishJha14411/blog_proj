# tests/integration/test_interactions_routes.py
import uuid
import pytest
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.models.role import Role
from app.models.like import Like
from app.models.bookmarks import Bookmark
from app.dependencies import get_current_user

pytestmark = pytest.mark.integration


# --- helpers ---------------------------------------------------------------

def _ensure_role(db: Session, name: str) -> Role:
    role = db.query(Role).filter(Role.name == name).one_or_none()
    if role:
        return role
    from tests.factories import RoleFactory
    return RoleFactory(name=name)

def _override_current_user(user):
    # FastAPI dep-override helper
    return lambda: user


# --- tests: LIKE -----------------------------------------------------------

def test_like_toggle_happy_path(client: TestClient, db_session: Session):
    from tests.factories import UserFactory, StoryFactory
    role = _ensure_role(db_session, "user")
    author = UserFactory(role=role)
    story = StoryFactory(user=author, is_published=True)

    # Acting user (not the author)
    actor = UserFactory(role=role)

    # Authenticate as actor
    client.app.dependency_overrides[get_current_user] = _override_current_user(actor)

    # 1) First call -> like created
    res1 = client.post(f"/stories/{story.id}/like")
    assert res1.status_code == 200, res1.text
    body1 = res1.json()
    assert body1["success"] is True and body1["liked"] is True

    exist = db_session.query(Like).filter_by(user_id=actor.id, story_id=story.id).first()
    assert exist is not None

    # 2) Second call -> like removed (toggle)
    res2 = client.post(f"/stories/{story.id}/like")
    assert res2.status_code == 200, res2.text
    body2 = res2.json()
    assert body2["success"] is True and body2["liked"] is False

    exist2 = db_session.query(Like).filter_by(user_id=actor.id, story_id=story.id).first()
    assert exist2 is None

    client.app.dependency_overrides.pop(get_current_user, None)


def test_like_404_for_missing_story(client: TestClient, db_session: Session):
    from tests.factories import UserFactory
    role = _ensure_role(db_session, "user")
    actor = UserFactory(role=role)
    client.app.dependency_overrides[get_current_user] = _override_current_user(actor)

    res = client.post(f"/stories/{uuid.uuid4()}/like")
    assert res.status_code == 404
    client.app.dependency_overrides.pop(get_current_user, None)


def test_like_triggers_notify_for_other_users(client: TestClient, db_session: Session, monkeypatch):
    from tests.factories import UserFactory, StoryFactory
    role = _ensure_role(db_session, "user")
    author = UserFactory(role=role)
    story = StoryFactory(user=author, is_published=True)
    actor = UserFactory(role=role)

    client.app.dependency_overrides[get_current_user] = _override_current_user(actor)

    called = {"count": 0, "args": None, "kwargs": None}

    def fake_notify(db, **kwargs):
        called["count"] += 1
        called["kwargs"] = kwargs

    monkeypatch.setattr("app.services.interactions.notify", fake_notify)

    res = client.post(f"/stories/{story.id}/like")
    assert res.status_code == 200
    assert called["count"] == 1
    # sanity: target points at the story
    assert str(called["kwargs"]["target_id"]) == str(story.id)

    client.app.dependency_overrides.pop(get_current_user, None)


def test_like_does_not_notify_when_liking_own_story(client: TestClient, db_session: Session, monkeypatch):
    from tests.factories import UserFactory, StoryFactory
    role = _ensure_role(db_session, "user")
    author = UserFactory(role=role)
    story = StoryFactory(user=author, is_published=True)

    client.app.dependency_overrides[get_current_user] = _override_current_user(author)

    count = {"n": 0}

    def fake_notify(*a, **k):
        count["n"] += 1

    monkeypatch.setattr("app.services.interactions.notify", fake_notify)

    res = client.post(f"/stories/{story.id}/like")
    assert res.status_code == 200
    assert count["n"] == 0

    client.app.dependency_overrides.pop(get_current_user, None)


def test_like_unauthenticated_401(client: TestClient):
    res = client.post(f"/stories/{uuid.uuid4()}/like")
    assert res.status_code == 401


# --- tests: BOOKMARK -------------------------------------------------------

def test_bookmark_toggle_and_listing(client: TestClient, db_session: Session):
    from tests.factories import UserFactory, StoryFactory
    role = _ensure_role(db_session, "user")
    user = UserFactory(role=role)
    s1 = StoryFactory(is_published=True)
    s2 = StoryFactory(is_published=True)

    client.app.dependency_overrides[get_current_user] = _override_current_user(user)

    # Toggle on s1 and s2
    r1 = client.post(f"/stories/{s1.id}/bookmark")
    r2 = client.post(f"/stories/{s2.id}/bookmark")
    assert r1.status_code == r2.status_code == 200
    assert r1.json()["bookmarked"] is True and r2.json()["bookmarked"] is True

    # Appears in listing
    lst = client.get("/users/me/bookmarks")
    assert lst.status_code == 200, lst.text
    data = lst.json()
    assert "items" in data and len(data["items"]) == 2
    returned_ids = {item["id"] for item in data["items"]}
    assert {str(s1.id), str(s2.id)} <= returned_ids

    # Toggle again to remove s1
    r3 = client.post(f"/stories/{s1.id}/bookmark")
    assert r3.status_code == 200
    assert r3.json()["bookmarked"] is False

    # DB reflects removal
    exist = db_session.query(Bookmark).filter_by(user_id=user.id, story_id=s1.id).first()
    assert exist is None

    client.app.dependency_overrides.pop(get_current_user, None)


def test_bookmark_404_for_missing_story(client: TestClient, db_session: Session):
    from tests.factories import UserFactory
    role = _ensure_role(db_session, "user")
    user = UserFactory(role=role)
    client.app.dependency_overrides[get_current_user] = _override_current_user(user)

    res = client.post(f"/stories/{uuid.uuid4()}/bookmark")
    assert res.status_code == 404

    client.app.dependency_overrides.pop(get_current_user, None)


def test_bookmarks_requires_auth_401(client: TestClient):
    res = client.get("/users/me/bookmarks")
    assert res.status_code == 401
