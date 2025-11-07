# tests/unit/services/test_admin_service.py
import uuid
import pytest
from sqlalchemy.orm import Session

import app.services.admin as admin_service
from app.models.user import User
from app.models.role import Role
from app.models.audit_log import AuditLog
from app.models.creator_request import CreatorRequest, RequestStatus

from app.schemas.admin import CreatorRequestCreate, CreatorRequestReview
from tests.factories import UserFactory, RoleFactory

# -----------------------
# list_users
# -----------------------

def test_list_users_returns_all(db_session: Session):
    u1 = UserFactory()
    u2 = UserFactory()
    users = admin_service.list_users(db_session)
    ids = {u.id for u in users}
    assert {u1.id, u2.id} <= ids

# -----------------------
# update_user
# -----------------------

def test_update_user_not_found_404(db_session: Session):
    with pytest.raises(Exception) as exc:
        admin_service.update_user(db_session, uuid.uuid4(), is_disabled=False, actor_id=uuid.uuid4())
    assert "not found" in str(exc.value).lower()

def test_update_user_changes_role_and_active_and_logs(db_session: Session):
    role_user = RoleFactory(name="user")
    role_creator = RoleFactory(name="creator")
    actor = UserFactory(role=role_creator)
    target = UserFactory(role=role_user)  # <-- no is_active kw

    out = admin_service.update_user(
        db_session,
        user_id=target.id,
        role_id=role_creator.id,
        is_disabled=True,          # <-- flip to disabled
        actor_id=actor.id,
    )
    assert out.role_id == role_creator.id
    assert out.is_disabled is True    # <-- assert model field

    logs = db_session.query(AuditLog).order_by(AuditLog.timestamp.desc()).all()
    last = logs[0]
    assert last.action == "update_user"
    assert last.target_id == str(target.id)
    assert (last.after_state or {}).get("is_disabled") is True
    assert (last.after_state or {}).get("role_id") == str(role_creator.id)

# -----------------------
# soft_delete_user
# -----------------------

def test_soft_delete_user_404(db_session: Session):
    with pytest.raises(Exception) as exc:
        admin_service.soft_delete_user(db_session, uuid.uuid4(), actor_id=uuid.uuid4())
    assert "not found" in str(exc.value).lower()

def test_soft_delete_user_sets_inactive_and_logs(db_session: Session):
    actor = UserFactory()
    target = UserFactory()  # <-- no is_active kw

    admin_service.soft_delete_user(db_session, target.id, actor_id=actor.id)
    db_session.refresh(target)
    assert target.is_disabled is True  # <-- assert model field

    log = db_session.query(AuditLog).order_by(AuditLog.timestamp.desc()).first()
    assert log.action == "soft_delete_user"
    assert (log.after_state or {}).get("is_disabled") is True

# -----------------------
# list_audit_logs
# -----------------------

def test_list_audit_logs_order_desc(db_session: Session):
    # Write two logs at different times
    actor = UserFactory()
    u = UserFactory()

    # first
    admin_service.update_user(db_session, u.id, is_disabled=False, actor_id=actor.id)
    # second
    admin_service.update_user(db_session, u.id, is_disabled=True, actor_id=actor.id)

    logs = admin_service.list_audit_logs(db_session)
    assert len(logs) >= 2
    # Most recent first
    assert logs[0].timestamp >= logs[1].timestamp

# -----------------------
# create_creator_request
# -----------------------

def test_create_creator_request_happy_path(db_session: Session):
    user_role = RoleFactory(name="user")
    user = UserFactory(role=user_role)
    req = admin_service.create_creator_request(
        db_session, user, CreatorRequestCreate(reason="I write often")
    )
    assert isinstance(req, CreatorRequest)
    assert req.status == RequestStatus.PENDING
    assert req.user_id == user.id  # <-- UUID vs str

def test_create_creator_request_conflict_if_pending_exists(db_session: Session):
    user = UserFactory(role=RoleFactory(name="user"))
    # seed a pending request
    admin_service.create_creator_request(db_session, user, CreatorRequestCreate(reason="first"))
    with pytest.raises(Exception) as exc:
        admin_service.create_creator_request(db_session, user, CreatorRequestCreate(reason="again"))
    assert "pending" in str(exc.value).lower()

def test_create_creator_request_reject_if_already_creator_or_higher(db_session: Session):
    creator = UserFactory(role=RoleFactory(name="creator"))
    with pytest.raises(Exception) as exc:
        admin_service.create_creator_request(db_session, creator, CreatorRequestCreate(reason="n/a"))
    assert "already a creator" in str(exc.value).lower()

# -----------------------
# get_pending_creator_requests
# -----------------------

def test_get_pending_creator_requests_filters_only_pending(db_session: Session):
    user = UserFactory(role=RoleFactory(name="user"))
    other = UserFactory(role=RoleFactory(name="user"))
    r1 = admin_service.create_creator_request(db_session, user, CreatorRequestCreate(reason="one"))
    r2 = admin_service.create_creator_request(db_session, other, CreatorRequestCreate(reason="two"))

    # manually approve one to ensure filter works
    r2.status = RequestStatus.APPROVED
    db_session.commit()

    pending = admin_service.get_pending_creator_requests(db_session)
    ids = {r.id for r in pending}
    assert r1.id in ids
    assert r2.id not in ids

# -----------------------
# review_creator_request
# -----------------------

def test_review_creator_request_404_for_missing_or_not_pending(db_session: Session):
    admin = UserFactory(role=RoleFactory(name="moderator"))
    # random UUID
    with pytest.raises(Exception):
        admin_service.review_creator_request(db_session, uuid.uuid4(), admin, CreatorRequestReview(action="approve"))

def test_review_creator_request_approve_happy_path(db_session: Session):
    # Ensure creator role exists
    RoleFactory(name="creator")

    admin = UserFactory(role=RoleFactory(name="moderator"))
    user = UserFactory(role=RoleFactory(name="user"))
    req = admin_service.create_creator_request(db_session, user, CreatorRequestCreate(reason="write!"))

    out = admin_service.review_creator_request(
        db_session, req.id, admin, CreatorRequestReview(action="approve")
    )
    db_session.refresh(user)

    assert out.status == RequestStatus.APPROVED
    assert user.role.name == "creator"
    assert out.reviewed_by_id == admin.id
    assert out.reviewed_at is not None

def test_review_creator_request_reject_path(db_session: Session):
    admin = UserFactory(role=RoleFactory(name="moderator"))
    user = UserFactory(role=RoleFactory(name="user"))
    req = admin_service.create_creator_request(db_session, user, CreatorRequestCreate(reason="nope"))

    out = admin_service.review_creator_request(
        db_session, req.id, admin, CreatorRequestReview(action="reject")
    )
    assert out.status == RequestStatus.REJECTED

def test_review_creator_request_invalid_action_400(db_session: Session):
    admin = UserFactory(role=RoleFactory(name="moderator"))
    user = UserFactory(role=RoleFactory(name="user"))
    req = admin_service.create_creator_request(db_session, user, CreatorRequestCreate(reason="ok"))

    with pytest.raises(Exception) as exc:
        admin_service.review_creator_request(db_session, req.id, admin, CreatorRequestReview(action="maybe"))
    assert "invalid action" in str(exc.value).lower()

def test_review_creator_request_approve_500_when_creator_role_missing(db_session: Session):
    # Ensure no creator role exists (clean up in case other tests created it)
    db_session.query(Role).filter(Role.name == "creator").delete(synchronize_session=False)
    db_session.commit()

    admin = UserFactory(role=RoleFactory(name="moderator"))
    user = UserFactory(role=RoleFactory(name="user"))
    req = admin_service.create_creator_request(db_session, user, CreatorRequestCreate(reason="ok"))

    with pytest.raises(Exception) as exc:
        admin_service.review_creator_request(db_session, req.id, admin, CreatorRequestReview(action="approve"))
    assert "creator role not found" in str(exc.value).lower()