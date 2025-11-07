import io
import uuid
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app import dependencies as deps
from app.models.role import Role
from app.models.user import User
from app.models.stories import Story, StoryStatus, ContentSource
from app.models.tags import Tag
from app.models.like import Like
from app.models.bookmarks import Bookmark
from app.schemas.stories import StoryCreate, StoryUpdate, StoryGenerateIn

from tests.factories import UserFactory, RoleFactory, StoryFactory, TagFactory

pytestmark = pytest.mark.integration


# -----------------------
# Helpers / dependency overrides
# -----------------------

def _ensure_role(db: Session, name: str = "creator") -> Role:
    r = db.query(Role).filter(Role.name == name).first()
    if not r:
        r = RoleFactory(name=name)
        db.add(r); db.commit(); db.refresh(r)
    return r

def _override_current_user(u: User):
    # FastAPI dependency override expects a no-arg callable returning the object
    def _dep():
        return u
    return _dep

def _override_require_roles(u: User):
    # require_roles("creator", ...) returns a dependency factory.
    # We bypass role checks and just return u for these tests.
    def _dep_factory(*_):
        def _inner():
            return u
        return _inner
    return _dep_factory


# -----------------------
# CREATE (human)
# -----------------------

def test_create_story_dedupes_tags_and_sets_published_when_not_flagged(client: TestClient, db_session: Session, monkeypatch):
    role = _ensure_role(db_session, "creator")
    user = UserFactory(role=role)

    # Moderation: not flagged
    monkeypatch.setattr("app.services.story.moderate_content", lambda items: (False, []))

    # require_roles & get_current_user
    from app import dependencies as deps
    client.app.dependency_overrides[deps.require_roles] = _override_require_roles(user)
    client.app.dependency_overrides[deps.get_current_user] = _override_current_user(user)

    res = client.post("/stories/", json={
        "title": "T",
        "content": "C",
        "header": None,
        "cover_image_url": None,
        "tag_names": ["a", "a", "b"],
        "is_published": True
    })
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["is_published"] is True
    assert sorted([t["name"] for t in body["tags"]]) == ["a", "b"]
    assert body["source"] == "user"

    # cleanup overrides
    client.app.dependency_overrides.pop(deps.require_roles, None)
    client.app.dependency_overrides.pop(deps.get_current_user, None)


def test_create_story_flagged_sets_draft_and_creates_flag_record(client: TestClient, db_session: Session, monkeypatch):
    role = _ensure_role(db_session, "creator")
    user = UserFactory(role=role)

    # Moderation: flagged with categories
    monkeypatch.setattr("app.services.story.moderate_content", lambda items: (True, ["profanity"]))

    from app import dependencies as deps
    client.app.dependency_overrides[deps.require_roles] = _override_require_roles(user)
    client.app.dependency_overrides[deps.get_current_user] = _override_current_user(user)

    res = client.post("/stories/", json={
        "title": "bad title",
        "content": "bad content",
        "tag_names": [],
        "is_published": True
    })
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["is_published"] is False  # forced draft when flagged
    assert body["source"] == "user"

    client.app.dependency_overrides.pop(deps.require_roles, None)
    client.app.dependency_overrides.pop(deps.get_current_user, None)


# -----------------------
# LIST / FILTERS
# -----------------------

def test_list_all_stories_only_published_for_anonymous(client: TestClient, db_session: Session):
    # one published, one draft
    s_pub = StoryFactory(is_published=True)
    s_draft = StoryFactory(is_published=False)

    res = client.get("/stories/")
    assert res.status_code == 200
    data = res.json()
    ids = {item["id"] for item in data["items"]}
    assert str(s_pub.id) in ids
    assert str(s_draft.id) not in ids


def test_list_all_stories_filter_by_tag_and_author(client: TestClient, db_session: Session):
    tag1 = TagFactory(name="tech")
    tag2 = TagFactory(name="life")

    author = UserFactory()
    s1 = StoryFactory(is_published=True, user=author, tags=[tag1])
    s2 = StoryFactory(is_published=True, tags=[tag2])
    s3 = StoryFactory(is_published=True, tags=[tag1, tag2])

    res = client.get(f"/stories/?tag=tech&author_id={author.id}")
    assert res.status_code == 200
    items = res.json()["items"]
    assert {i["id"] for i in items} == {str(s1.id)}  # only author+tech


# -----------------------
# DETAILS (computed fields & view logging)
# -----------------------

def test_read_story_details_computed_flags_and_view_log(client: TestClient, db_session: Session, monkeypatch):
    # create story + tag + interactions
    tag = TagFactory(name="x")
    user = UserFactory()
    story = StoryFactory(is_published=True, user=user, tags=[tag])

    viewer = UserFactory()
    from app import dependencies as deps
    client.app.dependency_overrides[deps.get_current_user_optional] = _override_current_user(viewer)

    # viewer has liked and bookmarked
    db_session.add_all([
        Like(user_id=viewer.id, story_id=story.id),
        Bookmark(user_id=viewer.id, story_id=story.id)
    ])
    db_session.commit()

    res = client.get(f"/stories/{story.id}")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == str(story.id)
    assert data["is_liked_by_user"] is True
    assert data["is_bookmarked_by_user"] is True
    assert data["tags"][0]["name"] == "x"

    client.app.dependency_overrides.pop(deps.get_current_user_optional, None)


# -----------------------
# UPDATE / DELETE (auth & moderation on update)
# -----------------------

def test_update_story_allows_owner_and_reflags_when_text_changes(client: TestClient, db_session: Session, monkeypatch):
    role = _ensure_role(db_session, "creator")
    owner = UserFactory(role=role)
    post = StoryFactory(user=owner, title="ok", content="ok", is_published=True)

    # Moderate to flagged on update
    monkeypatch.setattr("app.services.story.moderate_content", lambda items: (True, ["bad"]))

    from app import dependencies as deps
    client.app.dependency_overrides[deps.get_current_user] = _override_current_user(owner)

    res = client.patch(f"/stories/{post.id}", json={"title": "new", "content": "new"})
    assert res.status_code == 200
    body = res.json()
    assert body["is_published"] is False  # unpublished after flag
    client.app.dependency_overrides.pop(deps.get_current_user, None)


def test_delete_story_marks_deleted(client: TestClient, db_session: Session):
    role = _ensure_role(db_session, "creator")
    owner = UserFactory(role=role)
    post = StoryFactory(user=owner, is_published=False)

    from app import dependencies as deps
    client.app.dependency_overrides[deps.get_current_user] = _override_current_user(owner)

    res = client.delete(f"/stories/{post.id}")
    assert res.status_code == 204

    # should not appear in list
    res2 = client.get("/stories/")
    assert res2.status_code == 200
    ids = {i["id"] for i in res2.json()["items"]}
    assert str(post.id) not in ids

    client.app.dependency_overrides.pop(deps.get_current_user, None)


# -----------------------
# PUBLISH / UNPUBLISH
# -----------------------

def test_publish_and_unpublish_story(client: TestClient, db_session: Session):
    role = _ensure_role(db_session, "creator")
    owner = UserFactory(role=role)
    post = StoryFactory(user=owner, is_published=False, status=StoryStatus.draft)

    from app import dependencies as deps
    client.app.dependency_overrides[deps.get_current_user] = _override_current_user(owner)

    res = client.post(f"/stories/{post.id}/publish")
    assert res.status_code == 200
    assert res.json()["is_published"] is True

    res2 = client.post(f"/stories/{post.id}/unpublish")
    assert res2.status_code == 200
    assert res2.json()["is_published"] is False

    client.app.dependency_overrides.pop(deps.get_current_user, None)


# -----------------------
# AI: generate + feedback (mock LLM)
# -----------------------

def test_generate_ai_story_uses_llm_and_creates_revision(client: TestClient, db_session: Session, monkeypatch):
    role = _ensure_role(db_session, "creator")
    user = UserFactory(role=role)

    # No flagging
    monkeypatch.setattr("app.services.story.moderate_content", lambda items: (False, []))
    # Mock LLM
    monkeypatch.setattr("app.services.story._llm.generate", lambda prompt, model, temperature, max_tokens, timeout:
                        ("<h1>AI Title</h1><p>AI text</p>", "msg-1"))

    from app import dependencies as deps
    client.app.dependency_overrides[deps.get_current_user] = lambda: user

    res = client.post("/stories/generate", json={
        "prompt": "space opera",
        "model_name": "gpt-x",
        "temperature": 0.7,
        "publish_now": True,
        "genre": "scifi",
        "tone": "serious",
        "length_label": "short",
        "summary": "sum"
    })
    data = res.json()
    assert data["title"] != ""  # from default/first line
    assert data["source"] == "ai"

    client.app.dependency_overrides.pop(deps.get_current_user, None)
    assert res.status_code == 201, res.text


def test_feedback_regenerates_and_bumps_version(client: TestClient, db_session: Session, monkeypatch):
    # existing AI story
    role = _ensure_role(db_session, "creator")
    user = UserFactory(role=role)
    post = StoryFactory(user=user, source=ContentSource.ai, status=StoryStatus.generated, is_published=False, version=1)

    # Mock LLM + moderation
    monkeypatch.setattr("app.services.story._llm.generate", lambda *a, **k: ("<p>Regen</p>", "msg-regen"))
    monkeypatch.setattr("app.services.story.moderate_content", lambda items: (False, []))

    from app import dependencies as deps
    client.app.dependency_overrides[deps.get_current_user] = _override_current_user(user)

    res = client.post(f"/stories/{post.id}/feedback", json={"feedback": "faster pacing"})
    assert res.status_code == 200
    body = res.json()
    assert body["content"] == "<p>Regen</p>"

    client.app.dependency_overrides.pop(deps.get_current_user, None)
