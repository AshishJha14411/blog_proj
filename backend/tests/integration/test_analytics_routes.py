# tests/integration/test_analytics_routes.py
import uuid
import pytest
from datetime import date, timedelta, datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.routes.analytics import moderator_or_superadmin
from app.models.role import Role

pytestmark = pytest.mark.integration


# ----------------- helpers -----------------

def _ensure_role(db: Session, name: str) -> Role:
    existing = db.query(Role).filter(Role.name == name).one_or_none()
    if existing:
        return existing
    from tests.factories import RoleFactory
    return RoleFactory(name=name)

def _override_require_roles(user):
    # returns a dependency fn that yields `user`
    return lambda: user


# ----------------- auth gating -----------------

def test_analytics_endpoints_require_auth_401(client: TestClient):
    # no overrides -> all of these should be unauthorized
    assert client.get("/analytics/posts/daily").status_code == 401
    assert client.get("/analytics/users/daily").status_code == 401
    assert client.get("/analytics/flags").status_code == 401
    assert client.get("/analytics/moderation").status_code == 401
    assert client.get("/analytics/clicks").status_code == 401


# ----------------- /analytics/posts/daily -----------------

def test_posts_daily_dense_and_sorted(client: TestClient, db_session: Session):
    from tests.factories import UserFactory, StoryFactory
    role = _ensure_role(db_session, "moderator")
    moderator = UserFactory(role=role)

    today = date.today()
    d2 = today - timedelta(days=2)
    d5 = today - timedelta(days=5)

    # Make stories on two different days within the 7-day window
    StoryFactory(created_at=datetime(d2.year, d2.month, d2.day, 10, 0, 0))
    StoryFactory(created_at=datetime(d2.year, d2.month, d2.day, 12, 0, 0))
    StoryFactory(created_at=datetime(d5.year, d5.month, d5.day, 9, 30, 0))

    client.app.dependency_overrides[moderator_or_superadmin] = _override_require_roles(moderator)

    res = client.get("/analytics/posts/daily", params={"days": 7})

    client.app.dependency_overrides.pop(moderator_or_superadmin, None)

    assert res.status_code == 200, res.text
    body = res.json()
    stats = body["stats"]
    # dense series length == 7 days
    assert len(stats) == 7
    # sorted ascending by day
    days = [s["day"] for s in stats]
    assert days == sorted(days)

    # counts on specific days
    by_day = {s["day"]: s["count"] for s in stats}
    assert by_day[d2.isoformat()] >= 2
    assert by_day[d5.isoformat()] >= 1
    # total equals number created (allowing other tests to have data)
    assert sum(by_day.values()) >= 3


def test_posts_daily_days_validation_422(client: TestClient, db_session: Session):
    from tests.factories import UserFactory
    role = _ensure_role(db_session, "moderator")
    moderator = UserFactory(role=role)
    client.app.dependency_overrides[moderator_or_superadmin] = _override_require_roles(moderator)

    res = client.get("/analytics/posts/daily", params={"days": 0})

    client.app.dependency_overrides.pop(moderator_or_superadmin, None)

    assert res.status_code == 422


# ----------------- /analytics/users/daily -----------------

def test_users_daily_dense_and_sorted(client: TestClient, db_session: Session):
    from tests.factories import UserFactory
    role = _ensure_role(db_session, "moderator")
    moderator = UserFactory(role=role)

    today = date.today()
    d1 = today - timedelta(days=1)
    d3 = today - timedelta(days=3)

    # Create users with backdated created_at
    from tests.factories import UserFactory as UFactory
    UFactory(created_at=datetime(d1.year, d1.month, d1.day, 8, 0, 0))
    UFactory(created_at=datetime(d3.year, d3.month, d3.day, 18, 30, 0))
    UFactory(created_at=datetime(d3.year, d3.month, d3.day, 19, 0, 0))

    client.app.dependency_overrides[moderator_or_superadmin] = _override_require_roles(moderator)

    res = client.get("/analytics/users/daily", params={"days": 7})

    client.app.dependency_overrides.pop(moderator_or_superadmin, None)

    assert res.status_code == 200, res.text
    stats = res.json()["stats"]
    assert len(stats) == 7
    days = [s["day"] for s in stats]
    assert days == sorted(days)

    by_day = {s["day"]: s["count"] for s in stats}
    assert by_day[d1.isoformat()] >= 1
    assert by_day[d3.isoformat()] >= 2


# ----------------- /analytics/flags -----------------

def test_flags_breakdown_ai_vs_human(client: TestClient, db_session: Session):
    from tests.factories import UserFactory, FlagFactory
    role = _ensure_role(db_session, "moderator")
    moderator = UserFactory(role=role)

    # Ensure an 'automod' user exists
    automod = UserFactory(username="automod")
    human = UserFactory()

    # AI flags — IMPORTANT: pass the transient `flagged_by_user`, not *_id
    FlagFactory(flagged_by_user=automod)
    FlagFactory(flagged_by_user=automod)

    # Human flags
    FlagFactory(flagged_by_user=human)

    client.app.dependency_overrides[moderator_or_superadmin] = _override_require_roles(moderator)

    res = client.get("/analytics/flags")

    client.app.dependency_overrides.pop(moderator_or_superadmin, None)

    assert res.status_code == 200, res.text
    data = res.json()
    assert data["total"] >= 3
    assert data["ai_flags"] >= 2
    assert data["human_flags"] >= 1
    assert data["ai_flags"] + data["human_flags"] == data["total"]


# ----------------- /analytics/moderation -----------------

def test_moderation_logs_descending(client: TestClient, db_session: Session):
    """
    We don't have an AuditLogFactory in this repo, so this test only verifies:
      - endpoint returns 200 under correct auth
      - if any logs are returned, they're in descending order by timestamp
    """
    from tests.factories import UserFactory
    role = _ensure_role(db_session, "moderator")
    moderator = UserFactory(role=role)

    client.app.dependency_overrides[moderator_or_superadmin] = _override_require_roles(moderator)

    res = client.get("/analytics/moderation")

    client.app.dependency_overrides.pop(moderator_or_superadmin, None)

    assert res.status_code == 200, res.text
    logs = res.json()["logs"]
    # accept empty list; otherwise, ensure descending
    if logs:
        ts = [log["timestamp"] for log in logs]
        assert ts == sorted(ts, reverse=True)


# ----------------- /analytics/clicks -----------------

def test_clicks_daily_dense_and_sorted(client: TestClient, db_session: Session):
    from tests.factories import UserFactory, ClickFactory
    role = _ensure_role(db_session, "moderator")
    moderator = UserFactory(role=role)

    today = date.today()
    d0 = today
    d4 = today - timedelta(days=4)

    # Two clicks today, one 4 days ago
    ClickFactory(clicked_at=datetime(d0.year, d0.month, d0.day, 9, 0, 0))
    ClickFactory(clicked_at=datetime(d0.year, d0.month, d0.day, 15, 0, 0))
    ClickFactory(clicked_at=datetime(d4.year, d4.month, d4.day, 13, 0, 0))

    client.app.dependency_overrides[moderator_or_superadmin] = _override_require_roles(moderator)

    res = client.get("/analytics/clicks", params={"days": 5})

    client.app.dependency_overrides.pop(moderator_or_superadmin, None)

    assert res.status_code == 200, res.text
    stats = res.json()["stats"]
    assert len(stats) == 5
    days = [s["day"] for s in stats]
    assert days == sorted(days)

    by_day = {s["day"]: s["count"] for s in stats}
    assert by_day[d0.isoformat()] >= 2
    assert by_day[d4.isoformat()] >= 1
