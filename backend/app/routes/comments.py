from typing import Optional
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session

from app.schemas.comments import CommentCreate, CommentOut, CommentList
from app.services.comments import create_comment, list_comments, delete_comment
from app.dependencies import get_db, get_current_user, get_current_user_optional

router = APIRouter(tags=["Comments"])
# Missing the comment update route and services
@router.post("/posts/{post_id}/comments/", response_model= CommentOut, status_code= status.HTTP_201_CREATED)

def post_comment(post_id: int,data:CommentCreate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    return create_comment(db,post_id, data.content,current_user)


@router.get("/posts/{post}/comments/", response_model=CommentList, status_code=status.HTTP_200_OK)

def get_post_comments(post_id:int,limit: int = Query(10,gt=0,le=100),offset: int = Query(0,ge=0),db: Session= Depends(get_db),current_user = Depends(get_current_user_optional)):
    total,items  = list_comments(db,post_id,limit,offset)
    return CommentList(total=total,items=items)

@router.delete("/comments/{commend_id}",status_code = status.HTTP_204_NO_CONTENT)

def remove_comment(comment_id: int,db: Session= Depends(get_db), current_user=Depends(get_current_user)):
    delete_comment(db,comment_id, current_user)