# tests/unit/services/test_analytics_service.py

import uuid
from datetime import datetime, timedelta, date

import pytest
from sqlalchemy.orm import Session

import app.services.analytics as analytics_service
from app.services.system import get_automod_user

from app.models.user import User
from app.models.stories import Story
from app.models.flag import Flag
from app.models.audit_log import AuditLog
from app.models.impression import Impression
from app.models.click import Click, ClickableType
from app.models.analytics import AnalyticsCache
from app.schemas.analytics import DailyMetric

from tests.factories import UserFactory, RoleFactory, StoryFactory, AdFactory, ImpressionFactory, ClickFactory


def _midnight(d: date) -> datetime:
    return datetime(d.year, d.month, d.day)


# ---------------------------
# posts/users daily
# ---------------------------

def test_get_posts_daily_groups_by_day_and_respects_cutoff(db_session: Session):
    today = date.today()
    yesterday = today - timedelta(days=1)
    forty_days_ago = today - timedelta(days=40)

    author = UserFactory(role=RoleFactory(name="creator"))

    db_session.add_all([
        Story(id=uuid.uuid4(), user_id=author.id, title="old", content="x",
              created_at=_midnight(forty_days_ago), is_published=True),
        Story(id=uuid.uuid4(), user_id=author.id, title="y", content="x",
              created_at=_midnight(yesterday), is_published=True),
        Story(id=uuid.uuid4(), user_id=author.id, title="t1", content="x",
              created_at=_midnight(today), is_published=True),
        Story(id=uuid.uuid4(), user_id=author.id, title="t2", content="x",
              created_at=_midnight(today), is_published=True),
    ])
    db_session.commit()

    rows = analytics_service.get_posts_daily(db_session, days=30)
    assert rows[-2]["day"] == yesterday and rows[-2]["count"] == 1
    assert rows[-1]["day"] == today and rows[-1]["count"] == 2


def test_get_users_daily_groups_by_day_and_respects_cutoff(db_session: Session):
    today = date.today()
    two_days_ago = today - timedelta(days=2)
    thirty_one_days_ago = today - timedelta(days=31)

    role_id = RoleFactory(name="user").id
    db_session.add_all([
        User(id=uuid.uuid4(), email="a@example.com", username="a", password_hash="!",
             created_at=_midnight(two_days_ago), is_verified=True, role_id=role_id),
        User(id=uuid.uuid4(), email="b@example.com", username="b", password_hash="!",
             created_at=_midnight(today), is_verified=True, role_id=role_id),
        User(id=uuid.uuid4(), email="c@example.com", username="c", password_hash="!",
             created_at=_midnight(thirty_one_days_ago), is_verified=True, role_id=role_id),
    ])
    db_session.commit()

    rows = analytics_service.get_users_daily(db_session, days=30)
    days_only = {r["day"] for r in rows}
    assert two_days_ago in days_only
    assert today in days_only
    assert thirty_one_days_ago not in days_only

    counts = {r["day"]: r["count"] for r in rows}
    assert counts[two_days_ago] == 1
    assert counts[today] == 1


# ---------------------------
# flags breakdown
# ---------------------------

def test_get_flags_breakdown_ai_vs_human(db_session: Session):
    automod = get_automod_user(db_session)  # AI flags attributed to this user
    human = UserFactory(role=RoleFactory(name="moderator"))

    s1 = StoryFactory(user=UserFactory())
    s2 = StoryFactory(user=UserFactory())
    s3 = StoryFactory(user=UserFactory())

    db_session.add_all([
        Flag(id=uuid.uuid4(), flagged_by_user_id=automod.id, story_id=s1.id,
             reason="auto", status="open"),
        Flag(id=uuid.uuid4(), flagged_by_user_id=human.id,   story_id=s2.id,
             reason="human", status="open"),
        Flag(id=uuid.uuid4(), flagged_by_user_id=human.id,   story_id=s3.id,
             reason="human2", status="ignored"),
    ])
    db_session.commit()

    out = analytics_service.get_flags_breakdown(db_session)
    assert out["total"] == 3
    assert out["ai_flags"] == 1
    assert out["human_flags"] == 2


# ---------------------------
# moderation logs
# ---------------------------

def test_get_moderation_logs_order_desc(db_session: Session):
    from datetime import datetime, timedelta
    from app.models.audit_log import AuditLog
    from tests.factories import UserFactory, RoleFactory

    now = datetime.utcnow()
    older = now - timedelta(hours=1)

    # Create real users to satisfy FK audit_logs.actor_user_id -> users.id
    u1 = UserFactory(role=RoleFactory(name="moderator"))
    u2 = UserFactory(role=RoleFactory(name="moderator"))

    db_session.add_all([
        AuditLog(
            actor_user_id=u1.id,                 # <-- real FK
            action="approve",
            target_type="story",
            target_id=str(uuid.uuid4()),
            timestamp=older,
        ),
        AuditLog(
            actor_user_id=u2.id,                 # <-- real FK
            action="reject",
            target_type="story",
            target_id=str(uuid.uuid4()),
            timestamp=now,
        ),
    ])
    db_session.commit()

    logs = analytics_service.get_moderation_logs(db_session)
    assert len(logs) >= 2
    # ordered DESC by timestamp in the service
    assert logs[0].timestamp >= logs[1].timestamp


# ---------------------------
# clicks daily
# ---------------------------

def test_get_clicks_daily_groups_by_day(db_session: Session):
    today = date.today()
    yesterday = today - timedelta(days=1)

    # Satisfy NOT NULL clickable_type by pointing clicks at a Story
    st = StoryFactory()

    db_session.add_all([
        Click(id=uuid.uuid4(), clickable_type="story", clickable_id=st.id,
              clicked_at=_midnight(yesterday)),
        Click(id=uuid.uuid4(), clickable_type="story", clickable_id=st.id,
              clicked_at=_midnight(today)),
        Click(id=uuid.uuid4(), clickable_type="story", clickable_id=st.id,
              clicked_at=_midnight(today)),
    ])
    db_session.commit()

    rows = analytics_service.get_clicks_daily(db_session, days=2)
    assert rows[-2]["day"] == yesterday and rows[-2]["count"] == 1
    assert rows[-1]["day"] == today and rows[-1]["count"] == 2


# ---------------------------
# analytics cache -> series
# ---------------------------

def test_get_analytics_series_maps_rows_to_schema(db_session: Session):
    d1 = date.today() - timedelta(days=2)
    d2 = date.today() - timedelta(days=1)

    db_session.add_all([
        AnalyticsCache(
            id=uuid.uuid4(), day=d1, new_users=1, logins=5,
            stories_created=2, flags_created=1, ai_flags=1, human_flags=0
        ),
        AnalyticsCache(
            id=uuid.uuid4(), day=d2, new_users=2, logins=6,
            stories_created=4, flags_created=2, ai_flags=1, human_flags=1
        ),
    ])
    db_session.commit()

    out = analytics_service.get_analytics_series(db_session, start=d1, end=d2)
    assert len(out) == 2
    assert isinstance(out[0], DailyMetric)
    assert out[0].day == d1 and out[0].new_users == 1 and out[0].posts_created == 2
    assert out[1].day == d2 and out[1].logins == 6 and out[1].posts_created == 4


# ---------------------------
# ads CTR summary
# ---------------------------
def test_get_ads_ctr_summary_aggregates_imps_and_clicks(db_session: Session):
    # ARRANGE
    start = date.today() - timedelta(days=7)
    end = date.today()
    user = UserFactory()

    # Create valid Ads using the factory
    ad1 = AdFactory(advertiser_name="A1")
    ad2 = AdFactory(advertiser_name="A2")
    
    # Create 2 Impressions for Ad 1
    ImpressionFactory(ad=ad1, user=user, viewed_at=start + timedelta(days=1))
    ImpressionFactory(ad=ad1, user=user, viewed_at=start + timedelta(days=2))
    
    # Create 1 Impression for Ad 2
    ImpressionFactory(ad=ad2, user=user, viewed_at=start + timedelta(days=3))
    
    # Create 1 Click for Ad 1
    ClickFactory(clickable=ad1, user=user, clicked_at=start + timedelta(days=1))
    
    # Create 1 Click for Ad 2
    ClickFactory(clickable=ad2, user=user, clicked_at=start + timedelta(days=3))

    db_session.commit()

    # ACT
    rows = analytics_service.get_ads_ctr_summary(db_session, start, end)

    # ASSERT
    # Convert list of dicts to a dict keyed by ad_id for easy lookup
    summary_map = {row["ad_id"]: row for row in rows}
    
    # Check Ad 1
    assert ad1.id in summary_map
    r1 = summary_map[ad1.id]
    assert r1["impressions"] == 2
    assert r1["clicks"] == 1
    assert r1["ctr"] == 1 / 2

    # Check Ad 2
    assert ad2.id in summary_map
    r2 = summary_map[ad2.id]
    assert r2["impressions"] == 1
    assert r2["clicks"] == 1
    assert r2["ctr"] == 1 / 1