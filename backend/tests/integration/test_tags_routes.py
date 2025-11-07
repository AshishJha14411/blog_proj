# tests/integration/test_tags_routes.py
import uuid
import pytest
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.models.role import Role
from app.models.tags import Tag
from app.routes.tags import creator_or_superadmin, superadmin_only  # <-- import shared callables

pytestmark = pytest.mark.integration


# ---------- helpers ----------

def _ensure_role(db: Session, name: str) -> Role:
    existing = db.query(Role).filter(Role.name == name).one_or_none()
    if existing:
        return existing
    from tests.factories import RoleFactory
    return RoleFactory(name=name)

def _override_require_roles(user):
    # returns a dependency fn that yields `user`
    return lambda: user


# ---------- GET /tags ----------

def test_read_tags_returns_sorted(client: TestClient, db_session: Session):
    from tests.factories import TagFactory
    # create tags in unsorted order
    TagFactory(name="zeta")
    TagFactory(name="alpha")
    TagFactory(name="lambda")

    res = client.get("/tags/")
    assert res.status_code == 200, res.text
    data = res.json()
    assert "tags" in data
    names = [t["name"] for t in data["tags"]]
    assert names == sorted(names)  # must be sorted ASC by name
    # ensure id is serialized to string
    assert all(isinstance(t["id"], str) for t in data["tags"])


# ---------- POST /tags (creator or superadmin) ----------

def test_create_tag_requires_auth_401(client: TestClient):
    res = client.post("/tags/", json={"name": "newtag", "description": "d"})
    assert res.status_code == 401

def test_create_tag_success_with_creator(client: TestClient, db_session: Session):
    from tests.factories import UserFactory
    role = _ensure_role(db_session, "creator")
    user = UserFactory(role=role)

    client.app.dependency_overrides[creator_or_superadmin] = _override_require_roles(user)
    res = client.post("/tags/", json={"name": "backend", "description": "all about backend"})
    client.app.dependency_overrides.pop(creator_or_superadmin, None)

    assert res.status_code == 201, res.text
    body = res.json()
    assert body["name"] == "backend"
    assert body["description"] == "all about backend"
    assert isinstance(body["id"], str)
    # exists in DB
    assert db_session.query(Tag).filter_by(name="backend").first() is not None

def test_create_tag_conflict_409(client: TestClient, db_session: Session):
    from tests.factories import TagFactory, UserFactory
    TagFactory(name="dupe")

    role = _ensure_role(db_session, "creator")
    user = UserFactory(role=role)

    client.app.dependency_overrides[creator_or_superadmin] = _override_require_roles(user)
    res = client.post("/tags/", json={"name": "dupe", "description": None})
    client.app.dependency_overrides.pop(creator_or_superadmin, None)

    assert res.status_code == 409


# ---------- PATCH /tags/{id} (superadmin only) ----------

def test_update_tag_404(client: TestClient, db_session: Session):
    from tests.factories import UserFactory
    role = _ensure_role(db_session, "superadmin")
    user = UserFactory(role=role)

    client.app.dependency_overrides[superadmin_only] = _override_require_roles(user)
    res = client.patch(f"/tags/{uuid.uuid4()}", json={"name": "x", "description": "y"})
    client.app.dependency_overrides.pop(superadmin_only, None)

    assert res.status_code == 404

def test_update_tag_success_with_superadmin(client: TestClient, db_session: Session):
    from tests.factories import TagFactory, UserFactory
    tag = TagFactory(name="orig", description="d0")

    role = _ensure_role(db_session, "superadmin")
    user = UserFactory(role=role)

    client.app.dependency_overrides[superadmin_only] = _override_require_roles(user)
    res = client.patch(f"/tags/{tag.id}", json={"name": "renamed", "description": "d1"})
    client.app.dependency_overrides.pop(superadmin_only, None)

    assert res.status_code == 200, res.text
    body = res.json()
    assert body["name"] == "renamed"
    assert body["description"] == "d1"
    # persisted
    db_session.refresh(tag)
    assert tag.name == "renamed" and tag.description == "d1"

def test_update_tag_conflict_409(client: TestClient, db_session: Session):
    from tests.factories import TagFactory, UserFactory
    a = TagFactory(name="a")
    _ = TagFactory(name="b")

    role = _ensure_role(db_session, "superadmin")
    user = UserFactory(role=role)

    client.app.dependency_overrides[superadmin_only] = _override_require_roles(user)
    # rename "a" to existing "b" -> conflict
    res = client.patch(f"/tags/{a.id}", json={"name": "b"})
    client.app.dependency_overrides.pop(superadmin_only, None)

    assert res.status_code == 409


# ---------- DELETE /tags/{id} (superadmin only) ----------

def test_delete_tag_success_with_superadmin(client: TestClient, db_session: Session):
    from tests.factories import TagFactory, UserFactory
    tag = TagFactory(name="todel")

    role = _ensure_role(db_session, "superadmin")
    user = UserFactory(role=role)

    client.app.dependency_overrides[superadmin_only] = _override_require_roles(user)
    res = client.delete(f"/tags/{tag.id}")
    client.app.dependency_overrides.pop(superadmin_only, None)

    assert res.status_code == 204
    assert db_session.get(Tag, tag.id) is None

def test_delete_tag_404(client: TestClient, db_session: Session):
    from tests.factories import UserFactory
    role = _ensure_role(db_session, "superadmin")
    user = UserFactory(role=role)

    client.app.dependency_overrides[superadmin_only] = _override_require_roles(user)
    res = client.delete(f"/tags/{uuid.uuid4()}")
    client.app.dependency_overrides.pop(superadmin_only, None)

    assert res.status_code == 404
