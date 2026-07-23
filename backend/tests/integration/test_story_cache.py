# tests/integration/test_story_cache.py
"""End-to-end proof that story-list cache-aside works and invalidates properly."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

pytestmark = pytest.mark.integration


def _seed_published_story(db_session: Session, title: str = "cached-story"):
    from tests.factories import RoleFactory, UserFactory, StoryFactory
    RoleFactory(name="user")
    author = UserFactory(role=RoleFactory(name="creator"))
    return StoryFactory(user=author, title=title, is_published=True)


def test_anonymous_list_hits_cache_after_first_request(client: TestClient, db_session: Session, fake_redis):
    """Second identical anon request should hit Redis, not the DB."""
    _seed_published_story(db_session, "first-story")

    res1 = client.get("/stories/")
    assert res1.status_code == 200, res1.text

    # One key should now exist under our cache prefix.
    matched = list(fake_redis.scan_iter(match="cache:stories:list:*"))
    assert len(matched) == 1, f"expected exactly one list cache key, got {matched}"

    # Second call returns the cached payload verbatim.
    res2 = client.get("/stories/")
    assert res2.status_code == 200
    assert res2.json() == res1.json()


def test_story_create_invalidates_list_cache(client: TestClient, db_session: Session, fake_redis):
    """After a new story is created, the cached anon list must be wiped."""
    from tests.factories import RoleFactory, UserFactory
    from app.dependencies import get_current_user

    _seed_published_story(db_session, "seed-story")

    # Warm the cache.
    client.get("/stories/")
    assert list(fake_redis.scan_iter(match="cache:stories:list:*"))

    # Author a new story — this must invalidate the list cache.
    creator = UserFactory(role=RoleFactory(name="creator"))
    client.app.dependency_overrides[get_current_user] = lambda: creator
    try:
        res = client.post(
            "/stories/",
            json={
                "title": "brand new one",
                "content": "content body",
                "tag_names": [],
                "is_published": True,
            },
        )
        assert res.status_code == 201, res.text
    finally:
        client.app.dependency_overrides.pop(get_current_user, None)

    # The old list-page key must be gone.
    assert list(fake_redis.scan_iter(match="cache:stories:list:*")) == [], (
        "Story creation should have invalidated the story-list cache"
    )
