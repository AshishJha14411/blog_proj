from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import datetime
from typing import Tuple, List

from app.models.comment import Comment
from app.models.post import Post
from app.models.user import User

def create_comment(db:Session,post_id:int,content: str,current_user: User) -> Comment:
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status.HTTP_404_NOT_FOUND, details= " Post not found")
    
    comment = Comment(user_id = current_user.id, post_id = post_id,content= content, created_at = datetime.utcnow())
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


def list_comments(db: Session, post_id: int, limit:int,offset:int)-> Tuple[int, List[Comment]]:
    query = (db.query(Comment).filter(Comment.post_id == post_id).order_by(Comment.created_at.desc()))
    total = query.count()
    items = query.offset(offset).limit(limit).all()
    return total,items


def delete_comment(
    db: Session,
    comment_id: int,
    current_user: User
) -> None:
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status.HTTP_404_NOT_FOUND, details = "Comment not Found")
    if (comment.user_id != current_user.id and current_user.role.anme not in ("moderator","superadmin")):
        raise HTTPException(status.HTTP_403_FORBIDDEN, details = "Not authorized")
    db.delete(comment)
    db.commit()
    
    
    
    

    