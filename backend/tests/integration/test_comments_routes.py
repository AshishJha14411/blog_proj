# tests/integration/test_comments_routes.py
"""Integration tests that lock in the W3 PII fix and the CommentAuthorOut
contract on the public comments endpoint. These are the *guardrail* tests —
if someone reverts CommentAuthorOut back to UserOut, these fail immediately."""

import pytest
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.dependencies import get_current_user
from app.models.role import Role

pytestmark = pytest.mark.integration


def _ensure_role(db: Session, name: str) -> Role:
    role = db.query(Role).filter(Role.name == name).one_or_none()
    if role:
        return role
    from tests.factories import RoleFactory
    return RoleFactory(name=name)


def test_list_comments_never_leaks_email_or_pii(client: TestClient, db_session: Session):
    """W3 regression: `GET /stories/{id}/comments` is unauthenticated, so
    it must expose only `id / username / profile_image_url` for each author.
    Any regression that puts `UserOut` (which carries email + bio) back here
    would trip this test."""
    from tests.factories import UserFactory, StoryFactory, CommentFactory

    role = _ensure_role(db_session, "user")
    author = UserFactory(role=role, email="commenter@secret.example")
    story = StoryFactory(user=author, is_published=True)
    CommentFactory(user=author, story=story, content="hello world")

    # Explicitly unauthenticated — no auth override.
    res = client.get(f"/stories/{story.id}/comments")
    assert res.status_code == 200, res.text

    body = res.json()
    assert "items" in body and len(body["items"]) == 1

    item = body["items"][0]
    # Confirm we get the expected public author fields…
    assert set(item["user"].keys()) == {"id", "username", "profile_image_url"}

    # …and nothing that would be PII.
    forbidden = {"email", "bio", "is_verified", "social_links", "role"}
    assert not (forbidden & set(item["user"].keys())), (
        f"Public comment response leaked private fields: "
        f"{forbidden & set(item['user'].keys())}"
    )

    # Belt-and-suspenders: raw response text must not contain the email string,
    # even if the schema changes shape.
    assert "commenter@secret.example" not in res.text


def test_post_comment_response_also_uses_public_author_shape(client: TestClient, db_session: Session):
    """The POST response reuses `CommentOut` too — same PII contract applies."""
    from tests.factories import UserFactory, StoryFactory

    role = _ensure_role(db_session, "user")
    author = UserFactory(role=role, email="poster@secret.example")
    story = StoryFactory(user=UserFactory(role=role), is_published=True)

    client.app.dependency_overrides[get_current_user] = lambda: author
    try:
        res = client.post(
            f"/stories/{story.id}/comments",
            json={"content": "clean comment"},
        )
        assert res.status_code == 201, res.text

        body = res.json()
        assert set(body["user"].keys()) == {"id", "username", "profile_image_url"}
        assert "poster@secret.example" not in res.text
    finally:
        client.app.dependency_overrides.pop(get_current_user, None)


def test_post_comment_rejects_empty_and_oversized_content(client: TestClient, db_session: Session):
    """New schema caps (min_length=1, max_length=5000) must fire before any DB write."""
    from tests.factories import UserFactory, StoryFactory

    role = _ensure_role(db_session, "user")
    author = UserFactory(role=role)
    story = StoryFactory(user=UserFactory(role=role), is_published=True)

    client.app.dependency_overrides[get_current_user] = lambda: author
    try:
        # Whitespace-only strips to empty → 422.
        empty = client.post(f"/stories/{story.id}/comments", json={"content": "   "})
        assert empty.status_code == 422, empty.text

        # 6 KB blob → 422.
        oversized = client.post(
            f"/stories/{story.id}/comments",
            json={"content": "x" * 6000},
        )
        assert oversized.status_code == 422, oversized.text
    finally:
        client.app.dependency_overrides.pop(get_current_user, None)
