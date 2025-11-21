# app/services/auth.py

import random
import os
import secrets
from datetime import datetime, timedelta,timezone
from fastapi import BackgroundTasks, HTTPException, status,Depends
from sqlalchemy import or_
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer
from app.dependencies import get_db, get_password_hasher, get_mailer
from jose import JWTError
from app.models.user import User
from app.models.role import Role
from app.schemas.auth import LoginRequest, RefreshTokenRequest, TokenPair,MessageResponse,VerifyOtpRequest,UserUpdate,PasswordChangeRequest,ForgotPasswordRequest, ResetPasswordRequest
from app.models.otp_verification import OTPVerification
from app.utils.security import hash_password, create_access_token,verify_password,decode_access_token,create_refresh_token
from app.core.config import settings
from app.models.otp_verification import OTPVerification
from app.models.token_blacklist import TokenBlacklist
from app.models.password_reset_token import PasswordResetToken
import requests
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from app.models.oauth_accounts import OAuthAccount
from app.schemas.auth import GoogleLoginRequest
from typing import Tuple
from app.models.token_blacklist import TokenBlacklist


oauth2_scheme = OAuth2PasswordBearer(tokenUrl = "/auth/login")

def create_user(
    db: Session,
    data, # instance of SignUpRequest
    background_tasks:BackgroundTasks,
    hasher,# get password haser ()
    mailer
) -> tuple[User,TokenPair]:
    # hasing password for security purposes
    existing_user = db.query(User).filter(
        or_(
            User.email == data.email,
            User.username == data.username
        )
    ).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email or username already registered"
        )
    # Create user
    print(f"Password recieved is: {data}")
    hashed_pw = hasher.hash(data.password)
    raw_otp = f"{random.randint(100000,999999):06d}"
    user_role = db.query(Role).filter(Role.name == "user").first()
    role_name = "user"
    if os.getenv("E2E_TESTING") == "true" and "creator" in data.username:
        role_name = "creator"
    
    user_role = db.query(Role).filter(Role.name == role_name).first()
    if not user_role:
        user_role = db.query(Role).filter(Role.name == "user").first()
        # If 'user' role is also missing, your seed fixture is broken,
        # but this will prevent a 500 error.
        if not user_role:
             raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Critical: Role '{role_name}' not found."
            )
    # --- END FIX ---
    
    new_user = User(
        email=data.email,
        username = data.username,
        password_hash=hashed_pw,
        role_id = user_role.id
    )
    # db.commit()
    # db.refresh(user)
    
    otp_entry = OTPVerification(
        user = new_user,
        otp_code = hasher.hash(raw_otp),
        expires_at = datetime.utcnow() + timedelta(minutes=10)
    )
    db.add(new_user)
    db.add(otp_entry)
    # db.commit()
    
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error hashing password"
        )
    # Email Verification
    db.refresh(new_user)
    token = create_access_token(
        data={"user_id": str(new_user.id)},
        expires_delta=timedelta(hours=1)
    )
    verify_link = f"{settings.FRONTEND_URL}/verify-email?token={token}"
    link_body = (
        f"<p>Thanks for signing up, <strong>{new_user.username}</strong>!</p>"
        f"<p>Please verify your email by clicking <a href=\"{verify_link}\">here</a>.</p>"
    )
    background_tasks.add_task(
        mailer.send_email,
        new_user.email,
        "✅ Confirm Your Email Address",
        link_body
    )
    #OTP Email
    otp_body = (
        f"<p>Hi {new_user.username},</p>"
        f"<p>Your verification code is: <strong>{raw_otp}</strong></p>"
        "<p>This code expires in 10 minutes.</p>"
    )
    background_tasks.add_task(
        mailer.send_email,
        new_user.email,
        "🔒 Your OTP Verification Code",
        otp_body
    )
    access_token = create_access_token(data={"user_id": str(new_user.id)})
    refresh_token = create_refresh_token(
        data={"user_id": str(new_user.id)},
        expires_delta=timedelta(days=14)
    )
    tokens = TokenPair(access_token=access_token, refresh_token=refresh_token)
    return new_user,tokens

def login_user(db:Session, data:LoginRequest,hasher) -> TokenPair:
    user = db.query(User).filter(User.username == data.username).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail = "Invalid username or password"
        )
    access = create_access_token({"user_id": str(user.id)})
    refresh = create_refresh_token({"user_id": str(user.id)}, expires_delta=timedelta(days=14))
    tokens = TokenPair(access_token=access, refresh_token=refresh)
    
    # Return both the user and the tokens
    return user, tokens

def logout_user(db: Session, refresh_token: str):
    """
    Invalidates a user's session by blacklisting their refresh token.
    """
    try:
        payload = decode_access_token(refresh_token)
        
        if payload.get("type") != "refresh":
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid token type for logout.")
            
        jti = payload.get("jti")
        expires_at = datetime.fromtimestamp(payload.get("exp"), tz=timezone.utc)
        
        is_blacklisted = db.query(TokenBlacklist).filter(TokenBlacklist.jti == jti).first()
        if is_blacklisted:
            return

        blacklist_entry = TokenBlacklist(jti=jti, expires_at=expires_at)
        db.add(blacklist_entry)
        db.commit()
    except (JWTError, ValueError): # <-- CHANGE THIS (Catch jose error)
        # If the token is invalid/expired/malformed, we silently succeed
        pass
    
    return {"message": "You have been successfully logged out"}
    
    
def verify_email(token:str, db: Session) -> MessageResponse:
    try:
        payload = decode_access_token(token)
    except Exception:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail = " User not Found"
        )
    user = db.query(User).get(payload.get("user_id"))
    if user.is_verified:
        return MessageResponse(message = "Email is Verified")
    user.is_verified = True
    db.commit()
    return MessageResponse(message="Email is verified Successfully")


def verify_otp(data: VerifyOtpRequest, db: Session) -> MessageResponse:
    # 1) Find the user by email
    user = db.query(User).filter_by(email=data.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not Found"
        )

    # 2) Get the most recent, unused OTP entry for this user
    otp = (
        db.query(OTPVerification)
        .filter(OTPVerification.user_id == user.id, OTPVerification.used.is_(False))
        .order_by(OTPVerification.expires_at.desc())
        .first()
    )

    # 3) Validate existence, expiry, and the code via hash-verify
    if (
        not otp
        or otp.expires_at < datetime.utcnow()
        or not verify_password(data.otp_code, otp.otp_code)  # compare raw vs hashed
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP"
        )

    # 4) Mark used, set user's flag, persist
    otp.used = True
    user.is_otp_verified = True
    db.commit()

    return MessageResponse(message="OTP verified successfully")

def update_profile(current: User, data: UserUpdate, db: Session) -> User:
    # Include fields the caller explicitly provided and ignore Nones
    payload = data.model_dump(exclude_none=True)   # <- key change

    # (Optional) if you prefer to also accept explicitly-set None for nullable fields,
    # use: payload = data.model_dump(exclude_unset=True)

    for field, value in payload.items():
        setattr(current, field, value)

    db.add(current)   # harmless if already in-session; ensures tracked
    db.commit()
    db.refresh(current)
    return current


def change_password(current:User, data:PasswordChangeRequest, hasher, db:Session):
    if not hasher.verify(data.old_password, current.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Incorrect old password")
    current.password_hash = hasher.hash(data.new_password)
    db.commit()
    return{"message": "Password changed successfully"}

def forgot_password(
    db: Session,
    data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    mailer
):
    """
    Handles a forgot password request. Finds the user, generates a reset token,
    and emails them a link.
    """
    user = db.query(User).filter(User.email == data.email).first()
    # IMPORTANT: To prevent user enumeration attacks, we always return a success message,
    # even if the user is not found. The email is only sent if they actually exist.
    if user:
        # 1. Generate a secure, URL-safe token
        raw_token = secrets.token_urlsafe(32)
        
        # 2. Create the database entry for the token
        reset_token = PasswordResetToken(
            user_id=user.id,
            token=raw_token, # Storing raw token as per your current model
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        db.add(reset_token)
        db.commit()
        
        # 3. Create the full reset link for the email
        reset_link = f"{settings.FRONTEND_URL}/reset-password?token={raw_token}"
        
        # 4. Email the link to the user in the background
        email_body = f"<p>Hi {user.username},</p><p>Please click <a href='{reset_link}'>here</a> to reset your password. This link is valid for 1 hour.</p>"
        background_tasks.add_task(
            mailer.send_email,
            user.email,
            "🔑 Password Reset Request",
            email_body
        )
        
    return {"message": "If an account with that email exists, a password reset link has been sent."}

def reset_password(db: Session, data: ResetPasswordRequest, hasher):
    """
    Resets a user's password using a valid token from the reset link.
    """
    # 1. Find the token in the database
    token_entry = db.query(PasswordResetToken).filter(PasswordResetToken.token == data.token).first()

    # 2. Validate the token
    if not token_entry or token_entry.used or token_entry.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset token."
        )

    # 3. Find the user associated with the token and update their password
    user = db.query(User).get(token_entry.user_id)
    if not user:
        # This case should be rare but is a good safeguard
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found.")
        
    user.password_hash = hasher.hash(data.new_password)
    token_entry.used = True # Mark the token as used to prevent reuse
    db.commit()
    
    return {"message": "Your password has been reset successfully."}

def refresh_access(db: Session, data: RefreshTokenRequest) -> tuple[User, TokenPair]:
    try:
        payload = decode_access_token(data.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token type for refresh.")
        
        # --- THE FIX IS HERE: Check the blacklist ---
        jti = payload.get("jti")
        is_blacklisted = db.query(TokenBlacklist).filter(TokenBlacklist.jti == jti).first()
        if is_blacklisted:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token has been revoked. Please log in again.")
        
    except (JWTError, HTTPException) as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token") from e

    user = db.query(User).get(payload.get("user_id"))
    if not user or user.is_disabled:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="User not found or disabled")

    # Issue a new access token
    new_access_token = create_access_token({"user_id": str(user.id)})
    
    # For now, we reuse the refresh token. A more advanced pattern is to rotate it.
    tokens = TokenPair(access_token=new_access_token, refresh_token=data.refresh_token)
    
    return user, tokens


def handle_google_login(
    db: Session,
    code: str, # We receive the one-time code from Google
    hasher
) -> tuple[User, TokenPair]:
    """
    Handles the entire server-side Google OAuth2 flow, ensuring the DB
    connection is not held open during the external API call.
    """
    
    # --- STEP 1: Perform the external network call FIRST ---
    # We do this *before* any database operations.
    try:
        token_res = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
            timeout=10,
        )
        token_res.raise_for_status()
        token_data = token_res.json()
        id_tok = token_data.get("id_token")
        if not id_tok:
            raise HTTPException(status_code=400, detail="No id_token from Google")

        claims = id_token.verify_oauth2_token(
            id_tok, google_requests.Request(), settings.GOOGLE_CLIENT_ID
        )
        subject = claims["sub"]
        email = claims.get("email")
        
    except (requests.RequestException, ValueError) as e:
        raise HTTPException(status_code=400, detail=f"Google token exchange failed: {e}")

    # --- STEP 2: Now that we have the Google data, do all database work ---
    # The database connection is active only for this short block of code.
    
    oauth_account = db.query(OAuthAccount).filter_by(provider="google", subject=subject).first()
    
    if oauth_account:
        user = oauth_account.user
    else:
        user = db.query(User).filter(User.email == email).first() if email else None
        if not user:
            # Create a new user
            user_role = db.query(Role).filter(Role.name == "user").first()
            user = User(
                email=email,
                username=f"{email.split('@')[0]}_{secrets.token_hex(4)}",
                password_hash=hasher.hash(secrets.token_urlsafe(16)),
                is_verified=True,
                role_id=user_role.id,
                profile_image_url=claims.get("picture"),
            )
            db.add(user)
            db.flush()
        
        new_oauth_account = OAuthAccount(user_id=user.id, provider="google", subject=subject)
        db.add(new_oauth_account)
    
    db.commit()
    db.refresh(user)

    # --- STEP 3: Issue your application's tokens ---
    access = create_access_token(data={"user_id": str(user.id)})
    refresh = create_refresh_token(data={"user_id": str(user.id)}, expires_delta=timedelta(days=14))
    tokens = TokenPair(access_token=access, refresh_token=refresh)
    
    return user, tokens


