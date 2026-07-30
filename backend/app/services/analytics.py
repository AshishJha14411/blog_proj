from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Dict, List, Tuple

from sqlalchemy import and_, cast, func, Date, text
from sqlalchemy.orm import Session

from app.models.analytics import AnalyticsCache
from app.models.audit_log import AuditLog
from app.models.click import Click, ClickableType
from app.models.flag import Flag
from app.models.impression import Impression
from app.models.stories import Story
from app.models.user import User
from app.schemas.analytics import DailyMetric


def _daily_series(db: Session, *, table: str, date_col: str, days: int) -> List[Dict]:
    """Dense daily counts + cumulative running total, in a SINGLE SQL query.

    Old approach: a sparse GROUP BY, then a Python loop to fill the zero-days.
    This does it all in Postgres:
    - `generate_series(...)` emits every day in the window (no gaps in Python).
    - a LEFT JOIN pulls the per-day counts (0 where there's no data).
    - `SUM(count) OVER (ORDER BY day)` is a window function giving the running
      cumulative total — the growth curve — for free.

    Bonus correctness: `current_date` is the DB's date, killing the old
    server-local `date.today()` timezone bug (FINDINGS G13). `table`/`date_col`
    are internal literals (never user input), so the f-string is injection-safe.
    """
    sql = text(
        f"""
        SELECT
            day,
            count,
            SUM(count) OVER (ORDER BY day) AS running_total
        FROM (
            SELECT
                gs::date AS day,
                COALESCE(agg.cnt, 0) AS count
            FROM generate_series(
                current_date - make_interval(days => :days_back),
                current_date,
                interval '1 day'
            ) AS gs
            LEFT JOIN (
                SELECT {date_col}::date AS d, count(*) AS cnt
                FROM {table}
                WHERE {date_col} >= current_date - make_interval(days => :days_back)
                GROUP BY 1
            ) AS agg ON agg.d = gs::date
        ) dense
        ORDER BY day
        """
    )
    rows = db.execute(sql, {"days_back": days - 1}).mappings().all()
    return [
        {"day": r["day"], "count": int(r["count"]), "running_total": int(r["running_total"])}
        for r in rows
    ]


def get_posts_daily(db: Session, days: int = 30) -> List[Dict]:
    return _daily_series(db, table="stories", date_col="created_at", days=days)


def get_users_daily(db: Session, days: int = 30) -> List[Dict]:
    return _daily_series(db, table="users", date_col="created_at", days=days)


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


def get_moderation_logs(db: Session, limit: int = 50, offset: int = 0) -> List[AuditLog]:
    # W5: bounded — audit-log tables grow forever, no request should ever fetch all.
    return (
        db.query(AuditLog)
        .order_by(AuditLog.timestamp.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def get_clicks_daily(db: Session, days: int = 30) -> List[Dict]:
    return _daily_series(db, table="clicks", date_col="clicked_at", days=days)


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
