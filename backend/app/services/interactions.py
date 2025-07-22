from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.like import Like
from app.models.bookmarks import Bookmark
from app.models.post import Post
from app.models.user import User

def toggle_like(db:Session, post_id:int, current_user: User) -> bool:
    post = db.query(Post).get(post_id)
    if not post:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Post not found")
    
    existing = (db.query(Like).filter_by(user_id=current_user.id,post_id=post_id).first())
    if existing:
        db.delete(existing)
        db.commit()
        return False
    else:
        like = Like(user_id=current_user.id, post_id=post_id)
        db.add(like)
        db.commit()
        return True
    
    
def toggle_bookmark(db:Session, post_id: int, current_user:User) -> bool:
    post = db.query(Post).get(post_id)
    if not post:
        raise HTTPException(status.HTTP_404_NOT_FOUND, details = "Post not found")
    
    existing = (db.query(Bookmark).filter_by(user_id=current_user.id, post_id=post_id).first())
    
    if existing:
        db.delete(existing)
        db.commit()
        return False
    else:
        bookmark = Bookmark(user_id=current_user.id, post_id=post_id)
        db.add(bookmark)
        db.commit()
        return True
    
def list_bookmarks(db:Session, current_user:User):
    # bookmarks = (db.query(Bookmark).filter_by(user_id = current_user.id).all())
    # posts = [db.query(Post).get(b.post_id) for b in bookmarks]
    posts = (
        db.query(Post)
          .join(Bookmark, Post.id == Bookmark.post_id)
          .filter(Bookmark.user_id == current_user.id)
          .all()
    )
    
    return posts