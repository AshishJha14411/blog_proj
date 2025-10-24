from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date, and_
from datetime import timedelta, date, datetime
from typing import List
from datetime import date
from app.models.analytics import AnalyticsCache
from app.schemas.analytics import DailyMetric
from app.models.impression import Impression
from app.models.click import Click
from app.models.stories import Story
from app.models.user import User
from app.models.flag import Flag
from app.models.audit_log import AuditLog
from app.models.click import Click

def get_posts_daily(db: Session, days: int = 30):
    cutoff = date.today() - timedelta(days=days-1)
    q = (
        db.query(
            cast(Story.created_at, Date).label("day"),
            func.count().label("count")
        )
        .filter(cast(Story.created_at, Date) >= cutoff)
        .group_by("day")
        .order_by("day")
    )
    return [ {"day": r.day, "count": r.count} for r in q ]

def get_users_daily(db: Session, days: int = 30):
    cutoff = date.today() - timedelta(days=days-1)
    q = (
        db.query(
            cast(User.created_at, Date).label("day"),
            func.count().label("count")
        )
        .filter(cast(User.created_at, Date) >= cutoff)
        .group_by("day")
        .order_by("day")
    )
    return [ {"day": r.day, "count": r.count} for r in q ]

def get_flags_breakdown(db: Session):
    total = db.query(func.count()).select_from(Flag).scalar()
    ai_count = db.query(func.count()).select_from(Flag).filter(Flag.flagged_by_user_id == None).scalar()
    human_count = total - ai_count
    return {"total": total, "ai_flags": ai_count, "human_flags": human_count}

def get_moderation_logs(db: Session):
    logs = (
        db.query(AuditLog)
          .order_by(AuditLog.timestamp.desc())
          .all()
    )
    return logs

def get_clicks_daily(db: Session, days: int = 30):
    cutoff = date.today() - timedelta(days=days-1)
    q = (
        db.query(
            cast(Click.clicked_at, Date).label("day"),
            func.count().label("count")
        )
        .filter(cast(Click.clicked_at, Date) >= cutoff)
        .group_by("day")
        .order_by("day")
    )
    return [ {"day": r.day, "count": r.count} for r in q ]


def get_analytics_series(db: Session, start: date, end: date) -> List[DailyMetric]:
    rows = (
        db.query(AnalyticsCache)
        .filter(and_(AnalyticsCache.day >= start, AnalyticsCache.day <= end))
        .order_by(AnalyticsCache.day.asc())
        .all()
    )
    return [
        DailyMetric(
            day=r.day,
            new_users=r.new_users,
            logins=r.logins,
            posts_created=r.posts_created,
            flags_created=r.flags_created,
            ai_flags=r.ai_flags,
            human_flags=r.human_flags,
            dau=r.dau,
            posts_viewed=r.posts_viewed,
            likes=r.likes,
            comments=r.comments,
            ad_impressions=r.ad_impressions,
            ad_clicks=r.ad_clicks,
        )
        for r in rows
    ]

def get_ads_ctr_summary(db: Session, start: date, end: date):
    # aggregate by ad (and optionally by slot from impressions)
    imps = (
        db.query(Impression.ad_id, Impression.slot, func.count().label("impressions"))
        .filter(func.date(Impression.viewed_at) >= start, func.date(Impression.viewed_at) <= end)
        .group_by(Impression.ad_id, Impression.slot)
        .all()
    )
    clicks = (
        db.query(Click.ad_id, func.count().label("clicks"))
        .filter(func.date(Click.clicked_at) >= start, func.date(Click.clicked_at) <= end)
        .group_by(Click.ad_id)
        .all()
    )

    clicks_by_ad = {a: c for (a, c) in clicks}
    out = []
    for ad_id, slot, imp in imps:
        c = clicks_by_ad.get(ad_id, 0)
        ctr = (c / imp) if imp else 0.0
        out.append({"ad_id": ad_id, "slot": slot, "impressions": imp, "clicks": c, "ctr": ctr})
    return out
