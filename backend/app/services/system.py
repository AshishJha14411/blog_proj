# app/services/system.py (A new file for system-level helpers)

from sqlalchemy.orm import Session
from app.models.user import User

_automod_user = None

def get_automod_user(db: Session) -> User:
    """
    Finds and caches the special 'automod' system user.
    """
    global _automod_user
    if _automod_user is None:
        _automod_user = db.query(User).filter(User.username == "automod").first()
    
    if _automod_user is None:
        # This should never happen if the database is seeded correctly
        raise RuntimeError("The 'automod' system user has not been seeded in the database.")
        
    return _automod_user