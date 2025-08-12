from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import datetime
from app.models.flag import Flag
from app.models.post import Post
from app.models.comment import Comment
from app.models.user import User
from better_profanity import profanity

# load default word list at import time
profanity.load_censor_words()

def flag_post(
    db: Session,post_id: int, reason: str, current_user: User
) -> Flag:
    post = db.get(Post,post_id)
    if not post:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Post not found")
    
    flag = Flag( flagged_by_user_id=current_user.id, post_id=post_id, comment_id= None,reason=reason.strip(),status="open", created_at=datetime.utcnow())
    db.add(flag)
    db.commit()
    db.refresh(flag)
    return flag

def flag_comment(db:Session, comment_id: int, reason:str, current_user: User) -> Flag:
    comment = db.get(Comment, comment_id)
    if not comment:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Comment not found")
    flag = Flag(flagged_by_user_id=current_user.id,post_id=None,comment_id=comment_id,reason=reason.strip(),status="open",created_at=datetime.utcnow())
    db.add(flag)
    db.commit()
    db.refresh(flag)
    return flag

def list_open_flags(db:Session)-> list[Flag]:
    return (db.query(Flag).filter(Flag.status =="open").order_by(Flag.created_at.desc()).all())

def resolve_flag(db: Session, flag_id: int, status_str: str, current_user: User) -> Flag:
    flag = db.get(Flag, flag_id)
    if not flag:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Flag not found")
    allowed = {"approved","rejected","ignored","resolved","open"}
    if status_str not in allowed:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid status")
    flag.status = status_str
    flag.resolved_by = current_user.id
    flag.resolved_at = datetime.utcnow()
    db.commit()
    db.refresh(flag)
    return flag

def moderate_content(texts: list[str]) -> tuple[bool, list[str]]:
    """
    Scan a list of text blocks for profanity.
    Returns (flagged: bool, categories: list[str]).
    """
    for text in texts:
        if profanity.contains_profanity(text):
            # we flag on any profanity found
            return True, ["profanity"]
    return False, []

from sqlalchemy.orm import Session
from datetime import datetime
from fastapi import HTTPException, status

from app.models.post import Post, StoryStatus
from app.models.flag import Flag
from app.models.user import User
from app.services.notifications import notify

def _close_open_flags(db: Session, post_id: int, resolver_id: int, decision: str, note: str = ""):
    flags = (db.query(Flag)
               .filter(Flag.post_id == post_id, Flag.status == "open")
               .all())
    for f in flags:
        f.status = decision  # "approved" or "rejected"
        f.resolved_by = resolver_id
        f.resolved_at = datetime.utcnow()
        # keep reason as-is; append moderator note if provided
        if note:
            f.reason = (f.reason or "") + f" | decision_note: {note}"

def approve_post(db: Session, post_id: int, moderator: User) -> Post:
    post = db.get(Post,post_id)
    if not post:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Post not found")

    # flip status/publish
    post.status = StoryStatus.published
    post.is_published = True
    post.is_flagged = False

    _close_open_flags(db, post_id, moderator.id, decision="approved", note="approved")

    db.commit()
    db.refresh(post)

    # notify author
    notify(
        db,
        recipient_id=post.user_id,
        actor_id=moderator.id,
        action="post_approved",
        target_type="post",
        target_id=post.id
    )

    return post

def reject_post(db: Session, post_id: int, moderator: User, reason: str = "") -> Post:
    post = db.get(Post,post_id)
    if not post:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Post not found")

    post.status = StoryStatus.rejected
    post.is_published = False
    post.is_flagged = True

    _close_open_flags(db, post_id, moderator.id, decision="rejected", note=reason or "rejected")

    db.commit()
    db.refresh(post)

    notify(
        db,
        recipient_id=post.user_id,
        actor_id=moderator.id,
        action="post_rejected",
        target_type="post",
        target_id=post.id
    )

    return post

def moderation_queue(
    db: Session,
    status_filter: str | None,
    author_id: int | None,
    tag: str | None,
    limit: int,
    offset: int
):
    q = db.query(Post).filter(Post.deleted_at == None)

    # Default: show items that need attention
    if status_filter:
        q = q.filter(Post.status == status_filter)
    else:
        q = q.filter(Post.is_flagged == True)

    if author_id:
        q = q.filter(Post.user_id == author_id)

    if tag:
        from app.models.tag import Tag
        q = q.join(Post.tags).filter(Tag.name == tag)

    total = q.count()
    items = (q.order_by(Post.created_at.desc())
               .offset(offset).limit(limit).all())
    return total, items
