from fastapi import Depends,HTTPException, status,Cookie
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.utils.security import pwd_context
from app.utils.email import Mailer
from app.core.config import settings
from app.models.user import User
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import joinedload
from jwt import PyJWTError
from app.utils.security import hash_password, create_access_token,verify_password,decode_access_token
from typing import Optional
oauth2_scheme = OAuth2PasswordBearer(tokenUrl = "/auth/login")
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_password_hasher():
    # returns a passlib CryptContext for hashing/verifying
    return pwd_context

def get_mailer():
    # returns a simple SMTP mailer
    return Mailer(
        server=settings.MAIL_SERVER,
        port=settings.MAIL_PORT,
        username=settings.MAIL_USERNAME,
        password=settings.MAIL_PASSWORD,
        sender_email=settings.MAIL_FROM,
        sender_name=settings.MAIL_FROM_NAME,
    )
bearer_scheme = HTTPBearer(auto_error=False)
def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme), # Makes header optional
    refresh_token: Optional[str] = Cookie(default=None), # Gets refresh token from cookie
    db: Session = Depends(get_db)
) -> User:
    
    auth_token = token
    # If no header token, try to issue a new one using the refresh cookie
    if not auth_token:
        if not refresh_token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
        
        # This part requires a refresh endpoint that uses the cookie
        # For simplicity, we'll assume a valid access token for now.
        # In a full implementation, you'd call your refresh logic here.
        pass # Placeholder for refresh logic

    if not auth_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        payload = decode_access_token(auth_token)
        user_id = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = db.query(User).get(user_id)
    if user is None or user.is_disabled:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or disabled")
        
    return user
def get_current_user_optional(
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db)
) -> User | None:
    if creds:
        try:
            payload = decode_access_token(creds.credentials)
            return db.get(User, payload.get("user_id"))
        except:
            return None
    return None

# Role‐based access control
def require_roles(*allowed_roles: str):
    def checker(current_user: User = Depends(get_current_user)):
        if current_user.role.name not in allowed_roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return current_user
    return checker

# Must import this for require_roles to work
# from app.services.auth import get_current_user