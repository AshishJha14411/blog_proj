# app/services/auth.py

import random
from datetime import datetime, timedelta
from fastapi import BackgroundTasks, HTTPException, status,Depends
from sqlalchemy import or_
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer
from app.dependencies import get_db, get_password_hasher, get_mailer
from jwt import PyJWTError
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshTokenRequest, TokenPair,MessageResponse,VerifyOtpRequest,UserUpdate,PasswordChangeRequest
from app.models.otp_verification import OTPVerification
from app.utils.security import hash_password, create_access_token,verify_password,decode_access_token
from app.core.config import settings
from app.models.otp_verification import OTPVerification
from app.models.token_blacklist import TokenBlacklist
oauth2_scheme = OAuth2PasswordBearer(tokenUrl = "/auth/login")

def create_user(
    db: Session,
    data, # instance of SignUpRequest
    background_tasks:BackgroundTasks,
    hasher,# get password haser ()
    mailer
) -> User:
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
    
    hashed_pw = hasher.hash(data.password)
    raw_otp = f"{random.randint(100000,999999):06d}"
    new_user = User(
        email=data.email,
        username = data.username,
        password_hash=hashed_pw,
        role_id = 1
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
        data={"user_id": new_user.id},
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

    return new_user

def login_user(db:Session, data:LoginRequest,hasher) -> TokenPair:
    user = db.query(User).filter(User.username == data.username).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail = "Invalid username or password"
        )
    access = create_access_token({"user_id": user.id})
    refresh = create_access_token(
        {"user_id": user.id},
        expires_delta=timedelta(days=14) #14 days expiry for long retained token boletoh refresh token
    )
    return TokenPair(access_token=access,refresh_token=refresh)

def logout_user(db:Session,refresh_token:str) -> None:
    try:
        payload = decode_access_token(refresh_token)
        jti = payload.get("jti")
        expires_at = datetime.fromtimestamp(payload.get("exp"))
        
        blacklist_entry = TokenBlacklist(jti=jti, expires_at=expires_at)
        db.add(blacklist_entry)
        db.commit()
    except Exception:
        pass
    
    return {"message":"You have been sucessfully logged out"}
    

def refresh_access(db:Session, data:RefreshTokenRequest) -> TokenPair:
    try:
        payload = decode_access_token(data.refresh_token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid refresh token"
        )
    user = db.query(User).get(payload.get("user_id"))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="User not found"
        )
    access = create_access_token(
        {"user_id": user.id}, expires_delta=timedelta(hours=12)
    )
    
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
    return MessageResponse("Email is verified Successfully")

def verify_otp(data: VerifyOtpRequest, db: Session) -> MessageResponse:
    #filter by email
    user = db.query(User).filter_by(email=data.email).first()
    if not user:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail="User not Found"
        )
        
    otp = {
        db.query(OTPVerification).filter_by(user_id=user.id, otp_code=data.otp_code, used = False).first()
    }
    if not otp or otp.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code = status.HTTP_400_NOT_FOUND,
            detail="Invalid or expired OTP"
        )
    otp.used =True
    user.is_otp_verified = True
    db.commit()
    return MessageResponse(message="OTP verified successfully")


def update_profile(current: User,data: UserUpdate,db: Session) -> User:
    for field, value in data.dict(exclue_unset=True).items():
        setattr(current, field,value)
    db.commit()
    db.refresh(current)
    return current

def change_password(current:User, data:PasswordChangeRequest, hasher, db:Session):
    if not hasher.verify(data.old_password, current.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Incorrect old password")
    current.password_hash = hasher.hash(data.new_password)
    db.commit()
    return{"message": "Password changed successfully"}