# tests/integration/test_ads_routes.py
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.models.role import Role
from app.models.ads import Ads

# we'll import the admin router to fetch its dependency callable
from app.routes import ads as ads_routes

pytestmark = pytest.mark.integration


# ----------------- helpers -----------------

def _ensure_role(db: Session, name: str) -> Role:
    existing = db.query(Role).filter(Role.name == name).one_or_none()
    if existing:
        return existing
    from tests.factories import RoleFactory
    return RoleFactory(name=name)

def _override_require_roles_with_user(user):
    """
    The admin APIRouter was created with `dependencies=[Depends(require_roles("superadmin"))]`.
    We need to override the *exact* function object that `require_roles("superadmin")` produced.
    We can pull it off the router instance.
    """
    # first dependency in the admin router is the one we want
    assert ads_routes.router.dependencies, "Admin router has no dependencies to override."
    dep_fn = ads_routes.router.dependencies[0].dependency
    return dep_fn, (lambda: user)


# ----------------- auth gating -----------------

def test_admin_endpoints_require_auth_401(client: TestClient):
    # public endpoints should work (but here we only check admin ones)
    assert client.post("/admin/ads/", json={}).status_code == 401
    assert client.patch(f"/admin/ads/{uuid.uuid4()}", json={}).status_code == 401
    assert client.delete(f"/admin/ads/{uuid.uuid4()}").status_code == 401


# ----------------- public listing & get -----------------

def test_public_list_ads_paginates_and_sorts_desc(client: TestClient, db_session: Session):
    from tests.factories import AdFactory
    from datetime import datetime, timedelta

    # older ad
    older = AdFactory(created_at=datetime.utcnow() - timedelta(days=1))
    # newer ad
    newer = AdFactory(created_at=datetime.utcnow())

    res = client.get("/ads/", params={"limit": 10, "offset": 0})
    assert res.status_code == 200, res.text
    body = res.json()

    # Your API returns only {"items": [...]}
    assert "items" in body
    items = body["items"]
    assert len(items) >= 2

    # should contain both
    ids = [i["id"] for i in items]
    assert str(newer.id) in ids and str(older.id) in ids

    # ensure items are sorted by created_at desc (newest first)
    timestamps = [i["created_at"] for i in items]
    assert timestamps == sorted(timestamps, reverse=True)


def test_public_get_ad_404(client: TestClient):
    res = client.get(f"/ads/{uuid.uuid4()}")
    assert res.status_code == 404

def test_public_get_ad_ok(client: TestClient, db_session: Session):
    from tests.factories import AdFactory
    ad = AdFactory()

    res = client.get(f"/ads/{ad.id}")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["id"] == str(ad.id)
    assert body["advertiser_name"] == ad.advertiser_name
    # some required fields
    assert "destination_url" in body and body["destination_url"] == ad.destination_url
    assert "ad_content" in body and body["ad_content"] == ad.ad_content


# ----------------- admin CRUD -----------------

def test_admin_create_update_delete_flow(client: TestClient, db_session: Session):
    from tests.factories import UserFactory

    # superadmin user
    role = _ensure_role(db_session, "superadmin")
    admin_user = UserFactory(role=role)

    # override the specific dependency function used by the admin router
    dep_fn, override = _override_require_roles_with_user(admin_user)
    client.app.dependency_overrides[dep_fn] = override

    # --- create
    payload = {
        "advertiser_name": "ACME Inc",
        "destination_url": "https://example.com/landing",
        "ad_content": "The best widgets in town!",
        "image_url": "https://example.com/banner.jpg",
        "weight": 1,
        "active": True,
        # schema supports tag_names, but service ignores it for now
        "tag_names": ["tech", "gadgets"],
    }
    create_res = client.post("/admin/ads/", json=payload)
    assert create_res.status_code == 201, create_res.text
    created = create_res.json()
    ad_id = created["id"]

    # persisted
    ad_row = db_session.get(Ads, uuid.UUID(ad_id))
    assert ad_row is not None
    assert ad_row.advertiser_name == "ACME Inc"
    assert ad_row.active is True

    # --- update
    patch = {
        "advertiser_name": "ACME Global",
        "active": False,
        "weight": 3,
        # try passing tag_names — should be ignored by service but must not 422
        "tag_names": ["updated"],
    }
    upd_res = client.patch(f"/admin/ads/{ad_id}", json=patch)
    assert upd_res.status_code == 200, upd_res.text
    updated = upd_res.json()
    assert updated["advertiser_name"] == "ACME Global"
    assert updated["active"] is False
    assert updated["weight"] == 3

    db_session.refresh(ad_row)
    assert ad_row.advertiser_name == "ACME Global"
    assert ad_row.active is False
    assert ad_row.weight == 3

    # --- delete
    del_res = client.delete(f"/admin/ads/{ad_id}")
    assert del_res.status_code == 204, del_res.text
    assert db_session.get(Ads, uuid.UUID(ad_id)) is None

    # remove override
    client.app.dependency_overrides.pop(dep_fn, None)

def test_admin_update_404(client: TestClient, db_session: Session):
    from tests.factories import UserFactory
    role = _ensure_role(db_session, "superadmin")
    admin_user = UserFactory(role=role)

    dep_fn, override = _override_require_roles_with_user(admin_user)
    client.app.dependency_overrides[dep_fn] = override

    res = client.patch(f"/admin/ads/{uuid.uuid4()}", json={"advertiser_name": "x"})
    assert res.status_code == 404

    client.app.dependency_overrides.pop(dep_fn, None)

def test_admin_delete_404(client: TestClient, db_session: Session):
    from tests.factories import UserFactory
    role = _ensure_role(db_session, "superadmin")
    admin_user = UserFactory(role=role)

    dep_fn, override = _override_require_roles_with_user(admin_user)
    client.app.dependency_overrides[dep_fn] = override

    res = client.delete(f"/admin/ads/{uuid.uuid4()}")
    assert res.status_code == 404

    client.app.dependency_overrides.pop(dep_fn, None)
