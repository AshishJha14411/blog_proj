from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Dict, List, Tuple

from sqlalchemy import and_, cast, func, Date
from sqlalchemy.orm import Session

from app.models.analytics import AnalyticsCache
from app.models.audit_log import AuditLog
from app.models.click import Click, ClickableType
from app.models.flag import Flag
from app.models.impression import Impression
from app.models.stories import Story
from app.models.user import User
from app.schemas.analytics import DailyMetric


def _date_range_inclusive(start: date, end: date) -> List[date]:
    days = []
    cur = start
    while cur <= end:
        days.append(cur)
        cur = cur + timedelta(days=1)
    return days


def _fill_daily_counts(rows: List[Tuple[date, int]], start: date, end: date) -> List[Dict]:
    """
    rows: list of (day, count) already aggregated by DATE.
    Returns a dense series [ {"day": d, "count": n}, ... ] for all days in [start, end].
    """
    by_day = {d: c for d, c in rows}
    out = []
    for d in _date_range_inclusive(start, end):
        out.append({"day": d, "count": int(by_day.get(d, 0))})
    return out


def get_posts_daily(db: Session, days: int = 30) -> List[Dict]:
    end = date.today()
    start = end - timedelta(days=days - 1)

    # group by DATE(created_at)
    rows = (
        db.query(
            cast(Story.created_at, Date).label("day"),
            func.count(Story.id).label("count"),
        )
        .filter(cast(Story.created_at, Date) >= start)
        .group_by("day")
        .order_by("day")
        .all()
    )
    # rows: List[Row(day=date, count=int)] -> List[Tuple[date, int]]
    tuples = [(r.day, r.count) for r in rows]
    return _fill_daily_counts(tuples, start, end)


def get_users_daily(db: Session, days: int = 30) -> List[Dict]:
    end = date.today()
    start = end - timedelta(days=days - 1)

    rows = (
        db.query(
            cast(User.created_at, Date).label("day"),
            func.count(User.id).label("count"),
        )
        .filter(cast(User.created_at, Date) >= start)
        .group_by("day")
        .order_by("day")
        .all()
    )
    tuples = [(r.day, r.count) for r in rows]
    return _fill_daily_counts(tuples, start, end)


def get_flags_breakdown(db: Session) -> Dict[str, int]:
    total = db.query(func.count(Flag.id)).scalar() or 0

    ai_count = (
        db.query(func.count(Flag.id))
        .join(User, User.id == Flag.flagged_by_user_id)
        .filter(User.username == "automod")
        .scalar()
        or 0
    )
    human_count = max(total - ai_count, 0)
    return {"total": total, "ai_flags": ai_count, "human_flags": human_count}


def get_moderation_logs(db: Session) -> List[AuditLog]:
    return (
        db.query(AuditLog)
        .order_by(AuditLog.timestamp.desc())
        .all()
    )


def get_clicks_daily(db: Session, days: int = 30) -> List[Dict]:
    end = date.today()
    start = end - timedelta(days=days - 1)

    rows = (
        db.query(
            cast(Click.clicked_at, Date).label("day"),
            func.count(Click.id).label("count"),
        )
        .filter(cast(Click.clicked_at, Date) >= start)
        .group_by("day")
        .order_by("day")
        .all()
    )
    tuples = [(r.day, r.count) for r in rows]
    return _fill_daily_counts(tuples, start, end)


def get_analytics_series(db: Session, start: date, end: date) -> List[DailyMetric]:
    rows = (
        db.query(AnalyticsCache)
        .filter(and_(AnalyticsCache.day >= start, AnalyticsCache.day <= end))
        .order_by(AnalyticsCache.day.asc())
        .all()
    )

    # Map model->schema with safe defaults. Note: stories_created -> posts_created
    items: List[DailyMetric] = []
    for r in rows:
        items.append(
            DailyMetric(
                day=r.day,
                new_users=getattr(r, "new_users", 0),
                logins=getattr(r, "logins", 0),
                posts_created=getattr(r, "stories_created", 0),
                flags_created=getattr(r, "flags_created", 0),
                ai_flags=getattr(r, "ai_flags", 0),
                human_flags=getattr(r, "human_flags", 0),
                dau=getattr(r, "dau", 0),
                posts_viewed=getattr(r, "posts_viewed", 0),
                likes=getattr(r, "likes", 0),
                comments=getattr(r, "comments", 0),
                ad_impressions=getattr(r, "ad_impressions", 0),
                ad_clicks=getattr(r, "ad_clicks", 0),
            )
        )
    return items


def get_ads_ctr_summary(db: Session, start: date, end: date) -> List[Dict]:
    # Impressions by ad_id
    imps_q = (
        db.query(
            Impression.ad_id,
            func.count(Impression.id).label("impressions"),
        )
        .filter(
            cast(Impression.viewed_at, Date) >= start,
            cast(Impression.viewed_at, Date) <= end,
        )
        .group_by(Impression.ad_id)
        .all()
    )
    imps_by_ad = {ad_id: int(imps) for ad_id, imps in imps_q}

    # Clicks by ad_id (Click.clickable_id) scoped to AD
    clicks_q = (
        db.query(
            Click.clickable_id,
            func.count(Click.id).label("clicks"),
        )
        .filter(
            Click.clickable_type == ClickableType.AD,
            cast(Click.clicked_at, Date) >= start,
            cast(Click.clicked_at, Date) <= end,
        )
        .group_by(Click.clickable_id)
        .all()
    )
    clicks_by_ad = {ad_id: int(c) for ad_id, c in clicks_q}

    all_ad_ids = set(imps_by_ad.keys()) | set(clicks_by_ad.keys())

    out: List[Dict] = []
    for ad_id in sorted(all_ad_ids):
        imp = imps_by_ad.get(ad_id, 0)
        clk = clicks_by_ad.get(ad_id, 0)
        ctr = float(clk) / imp if imp > 0 else 0.0
        out.append(
            {
                "ad_id": ad_id,
                "impressions": imp,
                "clicks": clk,
                "ctr": ctr,
            }
        )
    return out
