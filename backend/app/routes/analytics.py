from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.schemas.analytics import (
    PostsDaily,
    UsersDaily,
    FlagsBreakdown,
    ModerationLogs,
    AuditLogOut,
    ClicksDaily,
)
from app.services.analytics import (
    get_posts_daily,
    get_users_daily,
    get_flags_breakdown,
    get_moderation_logs,
    get_clicks_daily,
)
from app.dependencies import get_db, require_roles

# Expose a dependency var so tests can override exactly this object,
# consistent with moderation routes.
moderator_or_superadmin = require_roles("moderator", "superadmin")

router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"],
    dependencies=[Depends(moderator_or_superadmin)],
)


@router.get("/posts/daily", response_model=PostsDaily, status_code=status.HTTP_200_OK)
def posts_daily(
    db: Session = Depends(get_db),
    days: int = Query(30, ge=1, le=365),
):
    stats = get_posts_daily(db, days)
    return PostsDaily(stats=stats)


@router.get("/users/daily", response_model=UsersDaily, status_code=status.HTTP_200_OK)
def users_daily(
    db: Session = Depends(get_db),
    days: int = Query(30, ge=1, le=365),
):
    stats = get_users_daily(db, days)
    return UsersDaily(stats=stats)


@router.get("/flags", response_model=FlagsBreakdown, status_code=status.HTTP_200_OK)
def flags_breakdown(db: Session = Depends(get_db)):
    data = get_flags_breakdown(db)
    # `data` already matches the FlagsBreakdown fields
    return data


@router.get("/moderation", response_model=ModerationLogs, status_code=status.HTTP_200_OK)
def moderation_logs(db: Session = Depends(get_db)):
    logs = get_moderation_logs(db)
    # Convert models -> schema
    items = [AuditLogOut.model_validate(log) for log in logs]
    return ModerationLogs(logs=items)


@router.get("/clicks", response_model=ClicksDaily, status_code=status.HTTP_200_OK)
def clicks_daily(
    db: Session = Depends(get_db),
    days: int = Query(30, ge=1, le=365),
):
    stats = get_clicks_daily(db, days)
    return ClicksDaily(stats=stats)
