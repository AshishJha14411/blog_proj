# app/services/system.py
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.user import User
from app.models.role import Role

def get_automod_user(db: Session) -> User:
    """
    Return the canonical 'automod' system user.
    - Query each call (avoid global cache that goes stale across test rollbacks).
    - If missing, create it (idempotent within the current transaction).
    """
    user = db.query(User).filter(User.username == "automod").first()
    if user:
        return user

    # Ensure there's a role to attach. Prefer moderator/superadmin/creator.
    role = (
        db.query(Role)
        .filter(Role.name.in_(["moderator", "superadmin", "creator"]))
        .first()
    )
    if not role:
        role = Role(name="moderator", description="System moderator role")
        db.add(role)
        db.flush()  # ensure role.id

    # Create the automod user deterministically
    user = User(
        email="automod@system.local",
        username="automod",
        password_hash="!",     # not used to log in
        is_verified=True,
        role_id=role.id,
        profile_image_url=None,
    )
    db.add(user)
    try:
        db.flush()  # allocate user.id, or handle race
    except IntegrityError:
        db.rollback()
        # Another concurrent inserter (unlikely in unit tests) created it; fetch again.
        user = db.query(User).filter(User.username == "automod").first()
        if not user:
            raise
    return user
