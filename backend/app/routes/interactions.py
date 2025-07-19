from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.schemas.interactions import ToggleResponse, BookmarkList
from app.services.interactions import toggle_like, toggle_bookmark, list_bookmarks
from app.dependencies import get_db,get_current_user


router = APIRouter(tags=["Interactions"])

@router.post("/posts/{post_id}/like",response_model=ToggleResponse,status_code=status.HTTP_200_OK)

def like_post(post_id:int, db: Session = Depends(get_db),current_user = Depends(get_current_user)):
    liked = toggle_like(db,post_id,current_user)
    return ToggleResponse(success=True, liked=liked)

@router.post(
    "/posts/{post_id}/bookmark",
    response_model=ToggleResponse,
    status_code=status.HTTP_200_OK
)
def bookmark_post(post_id:int,db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    bookmarked = toggle_bookmark(db,post_id,current_user)
    return ToggleResponse(success= True, bookmarked=bookmarked)

@router.get(
    "/users/me/bookmarks",
    response_model=BookmarkList,
    status_code=status.HTTP_200_OK
)

def get_my_bookmarks(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    post = list_bookmarks(db,current_user)
    return BookmarkList(items=posts)