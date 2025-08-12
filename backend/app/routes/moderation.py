from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.schemas.moderation import (
    FlagCreate, FlagOut,
    FlagList, FlagResolveRequest
)
from app.services.moderation import (
    flag_post, flag_comment,
    list_open_flags, resolve_flag
)
from app.dependencies import get_db, require_roles , get_current_user


router = APIRouter(tags=["Moderation"])

# 1. Flag a post
@router.post(
    "/posts/{post_id}/flag",
    response_model=FlagOut,
    status_code=status.HTTP_201_CREATED
)
def post_flag(
    post_id: int,
    data: FlagCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return flag_post(db, post_id, data.reason, current_user)

# 2. Flag a comment
@router.post(   
    "/comments/{comment_id}/flag",
    response_model=FlagOut,
    status_code=status.HTTP_201_CREATED
)
def comment_flag(
    comment_id: int,
    data: FlagCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return flag_comment(db, comment_id, data.reason, current_user)

# 3. List open flags (moderators & superadmins only)
@router.get(
    "/moderation/flags/",
    response_model=FlagList,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles("moderator","superadmin"))]
)
def get_flags(
    db: Session = Depends(get_db)
):
    flags = list_open_flags(db)
    return FlagList(flags=flags)

# 4. Resolve or ignore a flag (moderators & superadmins only)
@router.patch(
    "/moderation/flags/{flag_id}",
    response_model=FlagOut,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles("moderator","superadmin"))]
)
def patch_flag(
    flag_id: int,
    data: FlagResolveRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("moderator","superadmin"))
):
    return resolve_flag(db, flag_id, data.status, current_user)


from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from app.dependencies import get_db, require_roles, get_current_user
from app.schemas.moderation import ModerationDecision
from app.schemas.posts import PostList, PostOut
from app.services.moderation import moderation_queue, approve_post, reject_post
from app.models.user import User

router = APIRouter(prefix="/moderation", tags=["Moderation"])

@router.get("/queue", response_model=PostList)
def list_queue(
    status_filter: str | None = Query(None),   # "draft"|"generated"|"published"|"rejected" or None
    author_id: int | None = Query(None),
    tag: str | None = Query(None),
    limit: int = Query(10, gt=0, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("moderator", "superadmin")),
):
    total, items = moderation_queue(db, status_filter, author_id, tag, limit, offset)
    validated = [PostOut.model_validate(i, from_attributes=True) for i in items]
    return PostList(total=total, limit=limit, offset=offset, items=validated)

@router.post("/posts/{post_id}/approve", response_model=PostOut)
def approve(
    post_id: int,
    body: ModerationDecision,
    db: Session = Depends(get_db),
    moderator: User = Depends(require_roles("moderator", "superadmin")),
):
    post = approve_post(db, post_id, moderator)
    return PostOut.model_validate(post, from_attributes=True)

@router.post("/posts/{post_id}/reject", response_model=PostOut)
def reject(
    post_id: int,
    body: ModerationDecision,
    db: Session = Depends(get_db),
    moderator: User = Depends(require_roles("moderator", "superadmin")),
):
    reason = (body.reason or body.note or "").strip()
    if not reason:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Reason is required to reject")
    post = reject_post(db, post_id, moderator, reason=reason)
    return PostOut.model_validate(post, from_attributes=True)
