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