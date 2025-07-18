from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks,Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.schemas.auth import PasswordChangeRequest, SignUpRequest, SignUpResponse, LoginRequest, RefreshTokenRequest, TokenPair, MessageResponse, UserProfile, UserUpdate,VerifyOtpRequest
from app.services.auth import  change_password, create_user, login_user, logout_user, update_profile,verify_email, verify_otp
from app.dependencies import get_db, get_password_hasher, get_mailer,get_current_user
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

@router.post("/login",response_model=TokenPair,status_code=status.HTTP_200_OK)
def login(data:LoginRequest,db: Session=Depends(get_db), hasher = Depends(get_password_hasher)):
    return login_user(db,data,hasher)

@router.post("/logout",response_model=MessageResponse,status_code=status.HTTP_200_OK)
def logout(data:RefreshTokenRequest, db:Session=Depends(get_db)):
    return logout_user(db=db,refresh_token=data.refresh_token)

@router.post("/refresh", response_model=TokenPair,status_code=status.HTTP_200_OK)
def refresh_token(data: RefreshTokenRequest,db:Session=Depends(get_db)):
    return refresh_access(db, data)

@router.get("/verify-email",response_model=MessageResponse, status_code=status.HTTP_200_OK)
def verfify_email_link(token: str = Query(..., description="Email-Verification JWT Token"), db:Session=Depends(get_db)):
    return verify_email(token, db)

@router.post("/verify-otp", response_model=MessageResponse,status_code=status.HTTP_200_OK)

def otp_verify(data:VerifyOtpRequest,db:Session=Depends(get_db)):
    return verify_otp(data,db)

@router.get("/me", response_model=UserProfile, status_code=status.HTTP_200_OK)

def read_users_me(current=Depends(get_current_user)):
    return current

@router.patch("/me", response_model=UserProfile, status_code=status.HTTP_200_OK) 

def patch_users_me(data: UserUpdate, current=Depends(get_current_user), db:Session = Depends(get_db)):
    return update_profile(current, data, db)

@router.patch("/me/password",status_code=status.HTTP_200_OK)

def patch_users_me_password(
    data: PasswordChangeRequest,
    current= Depends(get_current_user),
    hasher=Depends(get_password_hasher),
    db: Session= Depends(get_db)
):
    return change_password(current,data,hasher,db)




