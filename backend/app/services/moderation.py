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

def resolve_flag(db: Session, flag_id:int,status_str:str,current_user:User)-> Flag:
    flag =db.get(Flag,flag_id)
    if not flag:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Flag not found")
    if status_str not in ("resovled","ignored"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid Satus")
    
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
