from typing import Optional
from fastapi import APIRouter, Depends, status, Query, Request
from sqlalchemy.orm import Session
# from app.dependencies import get_current_user
from app.schemas.posts import PostCreate, PostUpdate, PostOut, PostList
from app.services.posts import (
    create_post, get_posts, get_post_details,
    update_post as svc_update, delete_post as svc_delete
)
from app.dependencies import (
    get_db, require_roles, get_current_user_optional,get_current_user
)

router = APIRouter(prefix="/posts", tags=["Posts"])

@router.post("/", response_model=PostOut,status_code=status.HTTP_201_CREATED,dependencies=[Depends(require_roles("creator","moderator","superadmin"))])
def create_new_post( data: PostCreate, db: Session= Depends(get_db),current_user = Depends(require_roles("creator","moderator","superadmin"))):
    return create_post(db,data,current_user)

@router.get("/",response_model=PostList, status_code = status.HTTP_200_OK)
def list_posts(limit: int = Query(10,gt=0,le=100),offset:int = Query(0,ge=0),tag: Optional[str] = Query(None),author_id: Optional[int]=Query(None),db:Session = Depends(get_db),current_user = Depends(get_current_user_optional)):
    total, items = get_posts(db, limit, offset, tag, author_id, current_user)
    return PostList(total=total,limit=limit, offset=offset,items=items)

@router.get("/{post_id}",response_model=PostOut,status_code=status.HTTP_200_OK)
def read_post(
    post_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_optional)
):
    return get_post_details(db, post_id,current_user, request)

@router.patch("/{post_id}",response_model=PostOut,status_code=status.HTTP_200_OK)
def patch_post(post_id: int, data:PostUpdate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    return svc_update(db,post_id,data,current_user)

@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)

def remove_post(post_id: int, db: Session=Depends(get_db),current_user = Depends(get_current_user)):
    svc_delete(db,post_id,current_user)

