# tests/integration/test_moderation_routes.py
import uuid
import io
import pytest
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.routes.moderation import moderator_or_superadmin
from app.dependencies import get_current_user
from app.models.role import Role
from app.models.flag import Flag
from app.models.stories import StoryStatus

pytestmark = pytest.mark.integration


# ----------------- helpers -----------------

def _ensure_role(db: Session, name: str) -> Role:
    existing = db.query(Role).filter(Role.name == name).one_or_none()
    if existing:
        return existing
    from tests.factories import RoleFactory
    return RoleFactory(name=name)

def _override_user(user):
    return lambda: user

def _override_require_roles(user):
    # returns a dependency fn that yields `user`
    return lambda: user


# ----------------- USER-FACING: flagging stories & comments -----------------

def test_flag_story_creates_flag(client: TestClient, db_session: Session):
    from tests.factories import UserFactory, StoryFactory
    user = UserFactory()
    story = StoryFactory()

    # auth override
    client.app.dependency_overrides[get_current_user] = _override_user(user)

    payload = {"reason": "inappropriate"}
    res = client.post(f"/stories/{story.id}/flag", json=payload)

    client.app.dependency_overrides.pop(get_current_user, None)

    assert res.status_code == 201, res.text
    body = res.json()
    assert body["reason"] == "inappropriate"
    assert body["status"] == "open"
    assert body["story_id"] == str(story.id)
    assert body["flagged_by_user_id"] == str(user.id)

    # persisted
    f = db_session.get(Flag, uuid.UUID(body["id"]))
    assert f is not None and f.status == "open" and f.story_id == story.id


def test_flag_story_404(client: TestClient, db_session: Session):
    from tests.factories import UserFactory
    user = UserFactory()
    client.app.dependency_overrides[get_current_user] = _override_user(user)

    res = client.post(f"/stories/{uuid.uuid4()}/flag", json={"reason": "x"})
    client.app.dependency_overrides.pop(get_current_user, None)

    assert res.status_code == 404


def test_flag_comment_creates_flag(client: TestClient, db_session: Session):
    from tests.factories import UserFactory, CommentFactory
    user = UserFactory()
    comment = CommentFactory()

    client.app.dependency_overrides[get_current_user] = _override_user(user)

    res = client.post(f"/comments/{comment.id}/flag", json={"reason": "spam"})
    client.app.dependency_overrides.pop(get_current_user, None)

    assert res.status_code == 201, res.text
    body = res.json()
    assert body["comment_id"] == str(comment.id)
    assert body["reason"] == "spam"
    assert body["status"] == "open"
    # DB check
    f = db_session.get(Flag, uuid.UUID(body["id"]))
    assert f and f.comment_id == comment.id


# ----------------- ADMIN/MODERATOR: flags list/resolve -----------------

def test_list_open_flags_requires_auth_401(client: TestClient):
    res = client.get("/moderation/flags")
    assert res.status_code == 401


def test_list_open_flags_returns_only_open_sorted_desc(client: TestClient, db_session: Session):
    from tests.factories import UserFactory, FlagFactory
    role = _ensure_role(db_session, "moderator")
    moderator = UserFactory(role=role)

    # make open & resolved flags
    f1 = FlagFactory(status="open")
    f2 = FlagFactory(status="open")
    _ = FlagFactory(status="resolved")

    # override the exact dependency object used by the route
    client.app.dependency_overrides[moderator_or_superadmin] = _override_require_roles(moderator)

    res = client.get("/moderation/flags")

    client.app.dependency_overrides.pop(moderator_or_superadmin, None)

    assert res.status_code == 200, res.text
    data = res.json()
    ids = [f["id"] for f in data["flags"]]
    # only open
    assert set(ids) == {str(f1.id), str(f2.id)}
    # newest first
    created = [f["created_at"] for f in data["flags"]]
    assert created == sorted(created, reverse=True)


def test_resolve_flag_success_and_audit_fields(client: TestClient, db_session: Session):
    from tests.factories import UserFactory, FlagFactory
    role = _ensure_role(db_session, "moderator")
    moderator = UserFactory(role=role)
    flag = FlagFactory(status="open")

    # override role + current_user (endpoint depends on both)
    client.app.dependency_overrides[moderator_or_superadmin] = _override_require_roles(moderator)
    client.app.dependency_overrides[get_current_user] = _override_user(moderator)

    res = client.patch(f"/moderation/flags/{flag.id}", json={"status": "resolved"})

    client.app.dependency_overrides.pop(moderator_or_superadmin, None)
    client.app.dependency_overrides.pop(get_current_user, None)

    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] == "resolved"

    db_session.refresh(flag)
    assert flag.status == "resolved"
    assert flag.resolved_by == moderator.id
    assert flag.resolved_at is not None


def test_resolve_flag_invalid_status_422(client: TestClient, db_session: Session):
    """
    Invalid enum-like value is rejected by request validation (Pydantic) => 422.
    """
    from tests.factories import UserFactory, FlagFactory
    role = _ensure_role(db_session, "moderator")
    moderator = UserFactory(role=role)
    flag = FlagFactory(status="open")

    client.app.dependency_overrides[moderator_or_superadmin] = _override_require_roles(moderator)
    client.app.dependency_overrides[get_current_user] = _override_user(moderator)

    res = client.patch(f"/moderation/flags/{flag.id}", json={"status": "nope"})

    client.app.dependency_overrides.pop(moderator_or_superadmin, None)
    client.app.dependency_overrides.pop(get_current_user, None)

    assert res.status_code == 422


def test_resolve_flag_404(client: TestClient, db_session: Session):
    from tests.factories import UserFactory
    role = _ensure_role(db_session, "moderator")
    moderator = UserFactory(role=role)

    client.app.dependency_overrides[moderator_or_superadmin] = _override_require_roles(moderator)
    client.app.dependency_overrides[get_current_user] = _override_user(moderator)

    res = client.patch(f"/moderation/flags/{uuid.uuid4()}", json={"status": "resolved"})

    client.app.dependency_overrides.pop(moderator_or_superadmin, None)
    client.app.dependency_overrides.pop(get_current_user, None)

    assert res.status_code == 404


# ----------------- ADMIN/MODERATOR: moderation queue -----------------

def test_queue_defaults_to_flagged_only_with_pagination(client: TestClient, db_session: Session):
    from tests.factories import UserFactory, StoryFactory
    role = _ensure_role(db_session, "moderator")
    moderator = UserFactory(role=role)

    # Make a mix
    flagged1 = StoryFactory(is_flagged=True)
    flagged2 = StoryFactory(is_flagged=True)
    _not_flagged = StoryFactory(is_flagged=False)

    client.app.dependency_overrides[moderator_or_superadmin] = _override_require_roles(moderator)

    res = client.get("/moderation/queue?limit=10&offset=0")

    client.app.dependency_overrides.pop(moderator_or_superadmin, None)

    assert res.status_code == 200, res.text
    data = res.json()
    assert data["total"] >= 2
    ids = [item["id"] for item in data["items"]]
    assert str(flagged1.id) in ids and str(flagged2.id) in ids
    # ensure not including non-flagged
    assert all(item["is_flagged"] for item in data["items"])


def test_queue_filters_by_status_author_and_tag(client: TestClient, db_session: Session):
    from tests.factories import UserFactory, StoryFactory, TagFactory
    role = _ensure_role(db_session, "moderator")
    moderator = UserFactory(role=role)

    author = UserFactory()
    t_scifi = TagFactory(name="scifi")
    t_poetry = TagFactory(name="poetry")

    s1 = StoryFactory(user=author, status=StoryStatus.published, is_flagged=False, tags=[t_scifi])
    s2 = StoryFactory(user=author, status=StoryStatus.rejected, is_flagged=True, tags=[t_poetry])
    _s3 = StoryFactory(status=StoryStatus.draft, is_flagged=True, tags=[t_scifi])

    client.app.dependency_overrides[moderator_or_superadmin] = _override_require_roles(moderator)

    # filter by status
    res_status = client.get("/moderation/queue", params={"status_filter": StoryStatus.published})
    assert res_status.status_code == 200
    assert all(item["status"] == StoryStatus.published for item in res_status.json()["items"])

    # filter by author
    res_author = client.get("/moderation/queue", params={"author_id": str(author.id)})
    assert res_author.status_code == 200
    assert all(item["user_id"] == str(author.id) for item in res_author.json()["items"])

    # filter by tag
    res_tag = client.get("/moderation/queue", params={"tag": "poetry"})
    assert res_tag.status_code == 200
    ids = [i["id"] for i in res_tag.json()["items"]]
    assert str(s2.id) in ids

    client.app.dependency_overrides.pop(moderator_or_superadmin, None)


# ----------------- ADMIN/MODERATOR: approve / reject -----------------

def test_approve_story_closes_flags_and_notifies(client: TestClient, db_session: Session, monkeypatch):
    from tests.factories import UserFactory, StoryFactory, FlagFactory
    role = _ensure_role(db_session, "moderator")
    moderator = UserFactory(role=role)
    author = UserFactory()
    story = StoryFactory(user=author, is_flagged=True, status=StoryStatus.draft)
    # open flags to be closed
    FlagFactory(story_id=story.id, status="open")
    FlagFactory(story_id=story.id, status="open")

    # capture notify
    calls = {}
    def fake_notify(db, recipient_id, actor_id, action, target_type, target_id):
        calls["args"] = dict(recipient_id=recipient_id, actor_id=actor_id, action=action, target_type=target_type, target_id=target_id)

    monkeypatch.setattr("app.services.moderation.notify", fake_notify)

    client.app.dependency_overrides[moderator_or_superadmin] = _override_require_roles(moderator)
    client.app.dependency_overrides[get_current_user] = _override_user(moderator)

    res = client.post(f"/moderation/stories/{story.id}/approve", json={"note": "Looks good"})

    client.app.dependency_overrides.pop(moderator_or_superadmin, None)
    client.app.dependency_overrides.pop(get_current_user, None)

    assert res.status_code == 200, res.text
    body = res.json()
    assert body["is_published"] is True

    db_session.refresh(story)
    assert story.is_published and story.status == StoryStatus.published and story.is_flagged is False

    # flags closed — query fresh
    closed = db_session.query(Flag).filter(Flag.story_id == story.id).all()
    assert closed and all(f.status == "approved" and f.resolved_by == moderator.id and f.resolved_at for f in closed)
    assert any("Moderator Note" in (f.reason or "") for f in closed)

    # notify called
    assert calls["args"]["recipient_id"] == author.id
    assert calls["args"]["actor_id"] == moderator.id
    assert calls["args"]["action"] == "story_approved"
    assert calls["args"]["target_type"] == "story"
    assert calls["args"]["target_id"] == story.id


def test_reject_story_requires_reason_400(client: TestClient, db_session: Session):
    from tests.factories import UserFactory, StoryFactory
    role = _ensure_role(db_session, "moderator")
    moderator = UserFactory(role=role)
    story = StoryFactory()

    client.app.dependency_overrides[moderator_or_superadmin] = _override_require_roles(moderator)
    client.app.dependency_overrides[get_current_user] = _override_user(moderator)

    res = client.post(f"/moderation/stories/{story.id}/reject", json={"reason": "   "})

    client.app.dependency_overrides.pop(moderator_or_superadmin, None)
    client.app.dependency_overrides.pop(get_current_user, None)

    assert res.status_code == 400
    assert res.json()["detail"] == "A reason is required to reject a story."


def test_reject_story_closes_flags_and_notifies(client: TestClient, db_session: Session, monkeypatch):
    from tests.factories import UserFactory, StoryFactory, FlagFactory
    role = _ensure_role(db_session, "moderator")
    moderator = UserFactory(role=role)
    author = UserFactory()
    story = StoryFactory(user=author, is_flagged=True, status=StoryStatus.draft)
    FlagFactory(story_id=story.id, status="open")

    calls = {}
    def fake_notify(db, recipient_id, actor_id, action, target_type, target_id):
        calls["args"] = dict(recipient_id=recipient_id, actor_id=actor_id, action=action, target_type=target_type, target_id=target_id)

    monkeypatch.setattr("app.services.moderation.notify", fake_notify)

    client.app.dependency_overrides[moderator_or_superadmin] = _override_require_roles(moderator)
    client.app.dependency_overrides[get_current_user] = _override_user(moderator)

    res = client.post(f"/moderation/stories/{story.id}/reject", json={"reason": "plagiarism"})

    client.app.dependency_overrides.pop(moderator_or_superadmin, None)
    client.app.dependency_overrides.pop(get_current_user, None)

    assert res.status_code == 200, res.text

    db_session.refresh(story)
    assert story.status == StoryStatus.rejected
    assert story.is_published is False
    assert story.is_flagged is True

    # flags closed — query fresh
    closed = db_session.query(Flag).filter(Flag.story_id == story.id).all()
    assert closed and all(f.status == "rejected" and f.resolved_by == moderator.id and f.resolved_at for f in closed)

    # notify called
    assert calls["args"]["recipient_id"] == author.id
    assert calls["args"]["actor_id"] == moderator.id
    assert calls["args"]["action"] == "story_rejected"


def test_admin_endpoints_require_auth_401(client: TestClient):
    # no overrides -> all of these should be unauthorized
    assert client.get("/moderation/flags").status_code == 401
    assert client.get("/moderation/queue").status_code == 401
    assert client.patch(f"/moderation/flags/{uuid.uuid4()}", json={"status": "resolved"}).status_code == 401
    assert client.post(f"/moderation/stories/{uuid.uuid4()}/approve", json={"note": ""}).status_code == 401
    assert client.post(f"/moderation/stories/{uuid.uuid4()}/reject", json={"reason": "x"}).status_code == 401


def test_approve_reject_404(client: TestClient, db_session: Session):
    from tests.factories import UserFactory
    role = _ensure_role(db_session, "moderator")
    moderator = UserFactory(role=role)

    client.app.dependency_overrides[moderator_or_superadmin] = _override_require_roles(moderator)
    client.app.dependency_overrides[get_current_user] = _override_user(moderator)

    sid = uuid.uuid4()
    assert client.post(f"/moderation/stories/{sid}/approve", json={"note": ""}).status_code == 404
    assert client.post(f"/moderation/stories/{sid}/reject", json={"reason": "x"}).status_code == 404

    client.app.dependency_overrides.pop(moderator_or_superadmin, None)
    client.app.dependency_overrides.pop(get_current_user, None)
