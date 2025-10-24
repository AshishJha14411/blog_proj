from fastapi import APIRouter, Depends, status, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List
import uuid

from app.dependencies import get_db, require_roles, get_current_user
from app.models.user import User
from app.schemas.moderation import FlagCreate, FlagOut, FlagList, FlagResolveRequest, ModerationDecision, UserSummary
from app.schemas.stories import StoryList, StoryOut
from app.services import moderation

# This router will handle all moderation-related endpoints
router = APIRouter(prefix="/moderation", tags=["Moderation"])

# This separate router is for user-facing actions like flagging
user_action_router = APIRouter(tags=["User Actions"])


# --- USER-FACING FLAGGING ENDPOINTS ---

@user_action_router.post("/stories/{story_id}/flag", response_model=FlagOut, status_code=status.HTTP_201_CREATED)
def flag_a_story(
    story_id: uuid.UUID,
    data: FlagCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    new_flag = moderation.flag_story(db, story_id, data.reason, current_user)
    # Manually build the response
    return FlagOut(
        id=str(new_flag.id),
        flagged_by_user_id=str(new_flag.flagged_by_user_id),
        story_id=str(new_flag.story_id) if new_flag.story_id else None,
        comment_id=str(new_flag.comment_id) if new_flag.comment_id else None,
        reason=new_flag.reason,
        status=new_flag.status,
        created_at=new_flag.created_at,
        flagged_by=UserSummary.from_orm(new_flag.flagged_by)
    )

@user_action_router.post("/comments/{comment_id}/flag", response_model=FlagOut, status_code=status.HTTP_201_CREATED)
def flag_a_comment(
    comment_id: uuid.UUID,
    data: FlagCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    new_flag = moderation.flag_comment(db, comment_id, data.reason, current_user)
    # Manually build the response
    return FlagOut.from_orm(new_flag)


# --- ADMIN/MODERATOR ENDPOINTS ---

@router.get("/flags", response_model=FlagList, dependencies=[Depends(require_roles("moderator", "superadmin"))])
def get_open_flags(db: Session = Depends(get_db)):
    flags = moderation.list_open_flags(db)
    # Manually build the list response
    validated_flags = [FlagOut.from_orm(f) for f in flags]
    return FlagList(flags=validated_flags)

@router.patch("/flags/{flag_id}", response_model=FlagOut, dependencies=[Depends(require_roles("moderator", "superadmin"))])
def patch_flag_status(
    flag_id: uuid.UUID,
    data: FlagResolveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    resolved_flag = moderation.resolve_flag(db, flag_id, data.status, current_user)
    return FlagOut.from_orm(resolved_flag)

@router.get("/queue", response_model=StoryList, dependencies=[Depends(require_roles("moderator", "superadmin"))])
def list_moderation_queue(
    status_filter: str | None = Query(None),
    author_id: uuid.UUID | None = Query(None),
    tag: str | None = Query(None),
    limit: int = Query(10, gt=0, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    total, items = moderation.moderation_queue(db, status_filter, author_id, tag, limit, offset)
    validated = [StoryOut.from_orm(i) for i in items]
    return StoryList(total=total, limit=limit, offset=offset, items=validated)

@router.post("/stories/{story_id}/approve", response_model=StoryOut, dependencies=[Depends(require_roles("moderator", "superadmin"))])
def approve_a_story(
    story_id: uuid.UUID,
    body: ModerationDecision,
    db: Session = Depends(get_db),
    moderator: User = Depends(get_current_user),
):
    story = moderation.approve_story(db, story_id, moderator, note=body.note)
    return StoryOut.from_orm(story)

@router.post("/stories/{story_id}/reject", response_model=StoryOut, dependencies=[Depends(require_roles("moderator", "superadmin"))])
def reject_a_story(
    story_id: uuid.UUID,
    body: ModerationDecision,
    db: Session = Depends(get_db),
    moderator: User = Depends(get_current_user),
):
    reason = (body.reason or "").strip()
    if not reason:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="A reason is required to reject a story.")
    story = moderation.reject_story(db, story_id, moderator, reason=reason)
    return StoryOut.from_orm(story)
