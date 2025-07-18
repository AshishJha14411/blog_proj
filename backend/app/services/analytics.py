from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date
from datetime import timedelta, date, datetime

from app.models.post import Post
from app.models.user import User
from app.models.flag import Flag
from app.models.audit_log import AuditLog
from app.models.click import Click

def get_posts_daily(db: Session, days: int = 30):
    cutoff = date.today() - timedelta(days=days-1)
    q = (
        db.query(
            cast(Post.created_at, Date).label("day"),
            func.count().label("count")
        )
        .filter(cast(Post.created_at, Date) >= cutoff)
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
