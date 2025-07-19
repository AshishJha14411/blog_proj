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
