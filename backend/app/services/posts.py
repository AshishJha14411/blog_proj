from sqlalchemy.orm import Session
from typing import List, Optional, Tuple
from datetime import datetime
from fastapi import HTTPException, status, Request

from app.models.like import Like
from app.models.bookmarks import Bookmark
from app.models.post import Post
from app.models.tag import Tag
from app.models.view_history import ViewHistory
from app.schemas.posts import PostCreate, PostUpdate
from app.models.user import User
from app.services.moderation import moderate_content
from app.models.flag import Flag

def create_post(db:Session, data:PostCreate, current_user:User) -> Post:
    tag_objs = []
    for name in data.tags:
        tag = db.query(Tag).filter(Tag.name == name).first()
        if not tag:
            tag = Tag(name=name)
            db.add(tag)
            db.flush()
        tag_objs.append(tag)
    #profanity check
    flagged,cats = moderate_content([data.title,data.content])
    post = Post(user_id=current_user.id,title=data.title,header=data.header,content=data.content,cover_image_url=str(data.cover_image_url) if data.cover_image_url else None,is_published=(data.is_published and not flagged),is_flagged=flagged,flag_source="ai" if flagged else "none", created_at=datetime.utcnow(),updated_at=datetime.utcnow())
    post.tags = tag_objs
    db.add(post)
    db.flush()
    if flagged:
        flag = Flag(
            flagged_by_user_id = 1,
            post_id = post.id,
            reason="; ".join(cats) or "Profanity detected",status="open",
            created_at = datetime.utcnow()
        )
        db.add(flag)
    db.commit()
    db.refresh(post)
    return post


def get_posts(db:Session,limit:int, offset:int,tag:Optional[str],author_id:Optional[int],current_user: Optional[User])-> Tuple[int,List[Post]]:
    query = db.query(Post).filter(Post.deleted_at == None)
    if not (current_user and current_user.role.name in ("moderator","superadmin")):
        query = query.filter(Post.is_published == True)
    if author_id:
        query = query.filter(Post.user_id == author_id)
    if tag:
        query = query.join(Post.tags).filter(Tag.name == tag)
        
    total = query.count()
    items = (query.order_by(Post.created_at.desc()).offset(offset).limit(limit).all())
    
    return total, items

def get_post_details(db:Session, post_id:int,current_user:Optional[User],request: Request) -> Post:
    post = db.query(Post).filter(Post.id==post_id,Post.deleted_at == None).first()
    if not post:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Post not found")
    if not post.is_published:
        if not current_user or (
            post.user_id != current_user.id and current_user.role.name not in ("moderator", "superadmin")
        ):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Post Not Found")
        
    view  = ViewHistory(
        post_id=post.id,
        user_id = current_user.id if current_user else None,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent"),
        viewed_at = datetime.utcnow()
    )
    if current_user:
        # Check if a 'like' record exists for this user and post
        like = db.query(Like).filter_by(user_id=current_user.id, post_id=post.id).first()
        post.is_liked_by_user = True if like else False

        # Check if a 'bookmark' record exists
        bookmark = db.query(Bookmark).filter_by(user_id=current_user.id, post_id=post.id).first()
        post.is_bookmarked_by_user = True if bookmark else False
    
    db.add(view)
    db.commit()
    return post


def update_post(
    db:Session,
    post_id: int,
    data: PostUpdate,
    current_user:User
) -> Post:
    post = db.query(Post).get(post_id)
    if not post:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail = "Post not found")
    if post.user_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not authorized")
    changed = False
    fields_changed = []
    for field, val in data.dict(exclude_unset=True).items():
        setattr(post,field,val)
        fields_changed.append(field)
        
    if any(f in ("title","content")for f in fields_changed):
        flagged,cats = moderate_content([post.title,post.content])
        post.is_flagged = flagged
        post.flag_source = "ai" if flagged else post.flag_source
        if flagged:
            db.add(Flag(
                flagged_by_user_id=None,post_id=post.id,reason = "; ".join(cats) or "Profanity detected",
                status = "open",
                created_at = datetime.utcnow()
            ))
        post.is_published = False
    if fields_changed:
        post.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(post)
    return post

def delete_post(db:Session, post_id:int,current_user:User) -> None:
    post = db.query(Post).get(post_id)
    if not post:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Post not found")
    if (
        post.user_id != current_user.id and current_user.role.name not in ("moderator","superadmin")
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not Authorized")
    post.deleted_at = datetime.utcnow()
    db.commit()

def get_my_posts(db:Session,current_user: User, limit:int, offset:int) -> Tuple[int,List[Post]]:
    query = db.query(Post).filter(Post.user_id == current_user.id)
    total = query.count()
    items = (query.order_by(Post.created_at.desc()).offset(offset).limit(limit).all())
    
    return total, items

