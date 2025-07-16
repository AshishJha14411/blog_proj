from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks,Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.schemas.auth import PasswordChangeRequest, SignUpRequest, SignUpResponse, LoginRequest, RefreshTokenRequest, TokenPair, MessageResponse, UserProfile, UserUpdate,VerifyOtpRequest
from app.services.auth import  create_user
from app.dependencies import get_db, get_password_hasher, get_mailer
from app.models.user import User
from app.utils.rate_limiter import rate_limit
from app.utils.rate_limiter import signup_rate_limiter 


router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post(
    "/signup",
    response_model=SignUpResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(signup_rate_limiter)]
)
def signup(
    signup_data: SignUpRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    hasher = Depends(get_password_hasher),
    mailer = Depends(get_mailer),
):
    # 2. Create user + OTP + email in service
    user = create_user(
        db=db,
        data=signup_data,
        background_tasks=background_tasks,
        hasher=hasher,
        mailer=mailer
    )

    # 3. Return minimal response
    return SignUpResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        message="User created. Please check your email for verification."
    )
