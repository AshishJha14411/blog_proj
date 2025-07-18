from typing import Optional
from fastapi import APIRouter, Depends, status, Query, Request
from sqlalchemy.orm import Session
from app.services.auth import get_current_user
from app.schemas.posts import PostCreate, PostUpdate, PostOut, PostList
from app.services.posts import (
    create_post, get_posts, get_post_details,
    update_post as svc_update, delete_post as svc_delete
)
from app.dependencies import (
    get_db, require_roles, get_current_user_optional
)
from app.services.auth import get_current_user

router = APIRouter(prefix="/posts", tags=["Posts"])

@router.post("/", response_model=PostOut,status_code=status.HTTP_201_CREATED,dependencies=[Depends(require_roles("creator","moderator","superadmin"))])
def create_new_post( data: PostCreate, db: Session= Depends(get_db),current_user = Depends(require_roles("creator","moderator","superadmin"))):
    return create_post(db,data,current_user)