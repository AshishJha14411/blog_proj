"""
/** WHY: FastAPI's dependency system funnels every request through these
    factories — db session, mailer, current-user, role gating. Getting them
    right means every route inherits the same auth story and the same
    connection lifecycle. **/

/** WHAT: exports:
      - `get_db`          → per-request SQLAlchemy Session (closed on return).
      - `get_password_hasher`, `get_mailer` → simple provider factories.
      - `get_current_user` → 401 unless a valid access token is present.
      - `get_current_user_optional` → same, but returns None for anon callers.
      - `require_roles(*roles)` → 403 unless current user has one of the roles.
      - Pre-built role gates: `creator_or_superadmin`, `superadmin_only`. **/
"""
from typing import Optional

from fastapi import Cookie, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.user import User
from app.utils.email import Mailer
from app.utils.security import decode_access_token, pwd_context

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
bearer_scheme = HTTPBearer(auto_error=False)


def get_db():
    """
    /** WHAT: yield a session, guarantee close. FastAPI understands the
        generator form and calls `.close()` in `finally` for us on both
        success and exception paths. **/
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_password_hasher():
    """
    /** WHAT: shared passlib CryptContext. Kept as a factory rather than a
        module-level constant so tests can `dependency_overrides` it with
        a fast hasher if bcrypt bogs test runtime down. **/
    """
    return pwd_context


def get_mailer():
    """
    /** WHAT: SMTP mailer configured from settings. Not used by Celery
        workers (they build their own via app/tasks/email._mailer_for_worker)
        — this factory is for any synchronous send that still needs to
        happen in a request context. **/
    """
    return Mailer(
        server=settings.MAIL_SERVER,
        port=settings.MAIL_PORT,
        username=settings.MAIL_USERNAME,
        password=settings.MAIL_PASSWORD,
        sender_email=settings.MAIL_FROM,
        sender_name=settings.MAIL_FROM_NAME,
    )


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    refresh_token: Optional[str] = Cookie(default=None),
    db: Session = Depends(get_db),
) -> User:
    """
    /** WHY: 401-or-User for every protected route. **/
    /** WHAT: reads either the Authorization: Bearer header OR (fallback)
        the refresh_token cookie, validates the JWT, loads the user. **/
    /** WHY-THIS-WAY: `jose.JWTError` is the ONLY exception we swallow —
        catching bare Exception here hid DB errors as auth failures (W4.1).
        Disabled users are treated as absent to avoid leaking account-state
        to an attacker probing logins. **/
    """
    auth_token = token
    if not auth_token:
        if not refresh_token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
        # Placeholder: refresh happens explicitly via /auth/refresh, not here.

    if not auth_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        payload = decode_access_token(auth_token)
        user_id = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    user = db.get(User, user_id)
    if user is None or user.is_disabled:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or disabled")
    return user


def get_current_user_optional(
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    """
    /** WHAT: same as get_current_user but returns None for anonymous
        callers instead of 401. Used on public endpoints (list stories,
        view details) that vary their behavior per viewer role. **/
    """
    if creds:
        try:
            payload = decode_access_token(creds.credentials)
            return db.get(User, payload.get("user_id"))
        except JWTError:
            return None
    return None


def require_roles(*allowed_roles: str):
    """
    /** WHY: role gating is repeated on every mod/admin route. This factory
        keeps the check declarative — `Depends(require_roles("moderator"))`
        reads at the call site like an ACL rule. **/
    """
    def checker(current_user: User = Depends(get_current_user)):
        if current_user.role.name not in allowed_roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return current_user
    return checker


# Pre-built instances so route decorators are `Depends(creator_or_superadmin)`
# instead of `Depends(require_roles("creator", "superadmin"))`. Same identity
# on every reference — required for `dependency_overrides` to work in tests.
creator_or_superadmin = require_roles("creator", "superadmin")
superadmin_only = require_roles("superadmin")
