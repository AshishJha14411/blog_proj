# tests/integration/test_admin_routes.py
import uuid
import pytest
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.dependencies import get_current_user
from app.models.role import Role
from app.models.user import User
from app.models.audit_log import AuditLog
from app.models.creator_request import CreatorRequest, RequestStatus

pytestmark = pytest.mark.integration

# ---- helpers ----

def _ensure_role(db: Session, name: str) -> Role:
    existing = db.query(Role).filter(Role.name == name).one_or_none()
    if existing:
        return existing
    from tests.factories import RoleFactory
    return RoleFactory(name=name)

def _override_user(user):
    return lambda: user

# ----------------- USERS / AUDIT -----------------

def test_admin_list_users_requires_superadmin(client: TestClient):
    # no override -> 401
    res = client.get("/admin/users/")
    assert res.status_code == 401

def test_admin_list_users_ok_as_superadmin(client: TestClient, db_session: Session):
    from tests.factories import UserFactory
    role = _ensure_role(db_session, "superadmin")
    admin = UserFactory(role=role)

    # make a couple users
    _ = UserFactory()
    _ = UserFactory()

    client.app.dependency_overrides[get_current_user] = _override_user(admin)

    res = client.get("/admin/users/")
    client.app.dependency_overrides.pop(get_current_user, None)

    assert res.status_code == 200, res.text
    users = res.json()
    assert isinstance(users, list)
    assert len(users) >= 3  # admin + 2 created

def test_admin_update_user_changes_role_and_disabled_and_logs(client: TestClient, db_session: Session):
    from tests.factories import UserFactory
    super_role = _ensure_role(db_session, "superadmin")
    mod_role = _ensure_role(db_session, "moderator")
    admin = UserFactory(role=super_role)
    target = UserFactory()

    client.app.dependency_overrides[get_current_user] = _override_user(admin)

    payload = {"role_id": str(mod_role.id), "is_disabled": True}
    res = client.patch(f"/admin/users/{target.id}", json=payload)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["id"] == str(target.id)
    assert body["role"]["name"] == "moderator"
    assert body["is_disabled"] is True

    # audit log written
    logs = db_session.query(AuditLog).order_by(AuditLog.timestamp.desc()).all()
    assert logs and logs[0].action == "update_user"
    assert logs[0].actor_user_id == admin.id
    assert logs[0].target_id == str(target.id)
    assert logs[0].after_state.get("is_disabled") is True

    client.app.dependency_overrides.pop(get_current_user, None)

def test_admin_soft_delete_user_sets_disabled_and_logs(client: TestClient, db_session: Session):
    from tests.factories import UserFactory
    super_role = _ensure_role(db_session, "superadmin")
    admin = UserFactory(role=super_role)
    target = UserFactory()

    client.app.dependency_overrides[get_current_user] = _override_user(admin)

    res = client.delete(f"/admin/users/{target.id}")
    assert res.status_code == 204

    # refresh & check
    db_session.refresh(target)
    assert target.is_disabled is True

    log = db_session.query(AuditLog).order_by(AuditLog.timestamp.desc()).first()
    assert log and log.action == "soft_delete_user"
    assert log.actor_user_id == admin.id
    assert log.target_id == str(target.id)

    client.app.dependency_overrides.pop(get_current_user, None)

def test_admin_audit_logs_requires_superadmin_and_sorts_desc(client: TestClient, db_session: Session):
    from tests.factories import UserFactory
    super_role = _ensure_role(db_session, "superadmin")
    admin = UserFactory(role=super_role)

    # seed a couple logs
    db_session.add(AuditLog(
        actor_user_id=admin.id, action="a1", target_type="user", target_id=str(admin.id),
        after_state={}, timestamp=datetime.utcnow()
    ))
    db_session.add(AuditLog(
        actor_user_id=admin.id, action="a2", target_type="user", target_id=str(admin.id),
        after_state={}, timestamp=datetime.utcnow()
    ))
    db_session.commit()

    client.app.dependency_overrides[get_current_user] = _override_user(admin)

    res = client.get("/admin/audit-logs/")
    client.app.dependency_overrides.pop(get_current_user, None)

    assert res.status_code == 200, res.text
    data = res.json()
    ts = [entry["timestamp"] for entry in data["logs"]]
    assert ts == sorted(ts, reverse=True)

# ----------------- CREATOR REQUESTS -----------------

def test_submit_creator_request_and_reject_duplicate_pending(client: TestClient, db_session: Session):
    from tests.factories import UserFactory
    user = UserFactory()
    client.app.dependency_overrides[get_current_user] = _override_user(user)

    # first submit OK
    res1 = client.post("/admin/creator-requests", json={"reason": "I write cool stuff"})
    assert res1.status_code == 201, res1.text
    body = res1.json()
    assert body["user_id"] == str(user.id)
    assert body["status"] == RequestStatus.PENDING

    # duplicate pending -> 409
    res2 = client.post("/admin/creator-requests", json={"reason": "again"})
    client.app.dependency_overrides.pop(get_current_user, None)
    assert res2.status_code == 409

def test_list_pending_requires_moderator_or_superadmin(client: TestClient):
    res = client.get("/admin/creator-requests/pending")
    assert res.status_code == 401

def test_review_request_approve_and_promotes_role(client: TestClient, db_session: Session):
    from tests.factories import UserFactory, RoleFactory
    # ensure roles
    mod_role = _ensure_role(db_session, "moderator")
    creator_role = _ensure_role(db_session, "creator")
    moderator = UserFactory(role=mod_role)

    # normal user submits
    user = UserFactory(role=RoleFactory(name="user"))
    client.app.dependency_overrides[get_current_user] = _override_user(user)
    res_submit = client.post("/admin/creator-requests", json={"reason": "pls"})
    assert res_submit.status_code == 201
    request_id = res_submit.json()["id"]
    client.app.dependency_overrides.pop(get_current_user, None)

    # moderator reviews -> approve
    client.app.dependency_overrides[get_current_user] = _override_user(moderator)
    res_review = client.post(f"/admin/creator-requests/{request_id}/review", json={"action": "approve"})
    client.app.dependency_overrides.pop(get_current_user, None)

    assert res_review.status_code == 200, res_review.text
    body = res_review.json()
    assert body["status"] == RequestStatus.APPROVED
    # role promoted
    db_session.refresh(user)
    assert user.role.name == "creator"

def test_review_request_reject_flow(client: TestClient, db_session: Session):
    from tests.factories import UserFactory, RoleFactory
    mod_role = _ensure_role(db_session, "moderator")
    moderator = UserFactory(role=mod_role)

    # submit as regular user
    user = UserFactory(role=RoleFactory(name="user"))
    client.app.dependency_overrides[get_current_user] = _override_user(user)
    res_submit = client.post("/admin/creator-requests", json={"reason": "pls"})
    assert res_submit.status_code == 201
    request_id = res_submit.json()["id"]
    client.app.dependency_overrides.pop(get_current_user, None)

    # reject
    client.app.dependency_overrides[get_current_user] = _override_user(moderator)
    res_review = client.post(f"/admin/creator-requests/{request_id}/review", json={"action": "reject"})
    client.app.dependency_overrides.pop(get_current_user, None)

    assert res_review.status_code == 200, res_review.text
    assert res_review.json()["status"] == RequestStatus.REJECTED

def test_review_request_invalid_action_400(client: TestClient, db_session: Session):
    from tests.factories import UserFactory, RoleFactory
    mod_role = _ensure_role(db_session, "moderator")
    moderator = UserFactory(role=mod_role)

    # submit as user
    user = UserFactory(role=RoleFactory(name="user"))
    client.app.dependency_overrides[get_current_user] = _override_user(user)
    rid = client.post("/admin/creator-requests", json={"reason": "pls"}).json()["id"]
    client.app.dependency_overrides.pop(get_current_user, None)

    # invalid action
    client.app.dependency_overrides[get_current_user] = _override_user(moderator)
    res = client.post(f"/admin/creator-requests/{rid}/review", json={"action": "nope"})
    client.app.dependency_overrides.pop(get_current_user, None)

    assert res.status_code == 400
