from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks,Query, UploadFile, File,Response,Cookie,Header
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.schemas.auth import PasswordChangeRequest, SignUpRequest, SignUpResponse, LoginRequest, RefreshTokenRequest, TokenPair, MessageResponse, UserProfile, UserUpdate,VerifyOtpRequest,RoleOut,ForgotPasswordRequest, ResetPasswordRequest
from app.services.auth import forgot_password, reset_password
from app.schemas.user import UserOut
from app.services.auth import  change_password, create_user, login_user, logout_user, update_profile,verify_email, verify_otp,refresh_access
from app.dependencies import get_db, get_password_hasher, get_mailer,get_current_user
from app.models.user import User
from app.utils.cloudinary import upload_file
from app.utils.rate_limiter import rate_limit
from app.utils.rate_limiter import signup_rate_limiter 
from app.schemas.auth import GoogleLoginRequest,LoginResponse
from app.services.auth import handle_google_login
from fastapi import Response, Cookie
from fastapi.responses import RedirectResponse
import urllib.parse
from typing import Optional
import requests
from app.core.config import settings


router = APIRouter(prefix="/auth", tags=["Auth"])

IS_DEV = settings.FRONTEND_URL.startswith("http://")

COOKIE_SECURE   = not IS_DEV                # Secure only in prod
COOKIE_SAMESITE = "none" if not IS_DEV else "lax"
COOKIE_PATH     = "/auth"
# COOKIE_DOMAIN = settings.COOKIE_DOMAIN  # only set this in prod if you need cross-subdomain

def set_refresh_cookie(response: Response, token: str):
    response.set_cookie(
        key="refresh_token",
        value=token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=14 * 24 * 3600,
        path=COOKIE_PATH,
        # domain=COOKIE_DOMAIN,   # if you set this, also use it in delete_cookie
    )

def clear_refresh_cookie(response: Response):
    response.delete_cookie(
        key="refresh_token",
        path=COOKIE_PATH,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        # domain=COOKIE_DOMAIN,
    )

@router.post(
    "/signup",
    response_model=LoginResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(signup_rate_limiter)]
)
def signup(
    signup_data: SignUpRequest,
    response: Response,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    hasher = Depends(get_password_hasher),
    mailer = Depends(get_mailer),
):
    # 2. Create user + OTP + email in service
    user,tokens = create_user(
        db=db,
        data=signup_data,
        background_tasks=background_tasks,
        hasher=hasher,
        mailer=mailer
    )
    set_refresh_cookie(response, tokens.refresh_token)
    # 3. Return minimal response
    return LoginResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        user=UserProfile.from_orm(user)
    )

@router.post("/login",response_model=TokenPair,status_code=status.HTTP_200_OK)
def login(data: LoginRequest, response: Response,db: Session=Depends(get_db), hasher = Depends(get_password_hasher)):
     user, tokens= login_user(db,data,hasher)
     set_refresh_cookie(response, tokens.refresh_token)
     return LoginResponse(access_token=tokens.access_token, refresh_token=tokens.refresh_token, user=UserProfile.from_orm(user))

     

@router.post("/logout", response_model=MessageResponse, status_code=status.HTTP_200_OK)
def logout(
    response: Response,
    db: Session = Depends(get_db),
    refresh_cookie: Optional[str] = Cookie(None, alias="refresh_token"),
    authorization: Optional[str] = Header(None),
):
    token_to_revoke = refresh_cookie
    if not token_to_revoke and authorization and authorization.lower().startswith("bearer "):
        token_to_revoke = authorization.split(" ", 1)[1].strip()

    if token_to_revoke:
        print("[logout] blacklisting refresh token")
        logout_user(db, token_to_revoke)
    else:
        print("[logout] no refresh token provided via cookie or header")

    clear_refresh_cookie(response)  # expire the cookie
    return MessageResponse(message="You have been successfully logged out.")

@router.post("/refresh", response_model=LoginResponse) # Use LoginResponse
def refresh_token(
    response: Response,
    db: Session = Depends(get_db),
    refresh_token: Optional[str] = Cookie(None, alias="refresh_token"),
):
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token not found.")
    
    # This service needs to be updated to return the user object
    try:
        user, new_tokens = refresh_access(db, RefreshTokenRequest(refresh_token=refresh_token))
    except HTTPException as e:
        # If blacklisted/invalid, clear cookie so you don’t keep retrying a dead token
        clear_refresh_cookie(response)
        raise
    # We don't set a new refresh cookie unless we're rotating tokens
    # set_refresh_cookie(response, new_tokens.refresh_token)
    
    return LoginResponse(
        access_token=new_tokens.access_token,
        refresh_token=new_tokens.refresh_token,
        user=UserProfile.from_orm(user)
    )
    
    
    
@router.get("/verify-email",response_model=MessageResponse, status_code=status.HTTP_200_OK)
def verfify_email_link(token: str = Query(..., description="Email-Verification JWT Token"), db:Session=Depends(get_db)):
    return verify_email(token, db)

@router.post("/verify-otp", response_model=MessageResponse,status_code=status.HTTP_200_OK)

def otp_verify(data:VerifyOtpRequest,db:Session=Depends(get_db)):
    return verify_otp(data,db)

@router.get("/me", response_model=UserProfile, status_code=status.HTTP_200_OK)
def read_users_me(current: User = Depends(get_current_user)):
    """
    Returns the profile of the currently authenticated user.
    """
    # Instead of returning the raw 'current' object, we explicitly build
    # the UserProfile response to ensure all data types are correct.
    return UserProfile(
        id=str(current.id),  # Convert UUID to string
        email=current.email,
        username=current.username,
        is_verified=current.is_verified,
        profile_image_url=current.profile_image_url,
        social_links=current.social_links,
        bio=current.bio,
        total_posts=current.total_posts,
        total_likes=current.total_likes,
        total_comments=current.total_comments,
        role=RoleOut(
            id=str(current.role.id), # Convert nested UUID to string
            name=current.role.name
        )
    )

@router.patch("/me", response_model=UserProfile, status_code=status.HTTP_200_OK)
def patch_users_me(
    data: UserUpdate,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Updates the profile of the currently authenticated user.
    """
    updated_user = update_profile(current, data, db)

    # We apply the same explicit conversion here to ensure the response is valid.
    return UserProfile(
        id=str(updated_user.id),
        email=updated_user.email,
        username=updated_user.username,
        is_verified=updated_user.is_verified,
        profile_image_url=updated_user.profile_image_url,
        social_links=updated_user.social_links,
        total_posts=updated_user.total_posts,
        total_likes=updated_user.total_likes,
        bio=current.bio,
        total_comments=updated_user.total_comments,
        role=RoleOut(
            id=str(updated_user.role.id),
            name=updated_user.role.name
        )
    )

@router.post("/me/avatar", response_model=UserOut, status_code=status.HTTP_200_OK)
def upload_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Uploads a new profile picture for the currently authenticated user.
    """
    # 1. Upload the file to Cloudinary
    # We pass file.file, which is the file-like object.
    secure_url = upload_file(file.file, folder="profile_pictures")

    # 2. Update the user's profile_image_url in the database
    current_user.profile_image_url = secure_url
    db.commit()
    db.refresh(current_user)

    # 3. Return the updated user profile
    # We use the explicit pattern to avoid validation errors.
    return UserOut.from_orm(current_user)

@router.patch("/me/password",status_code=status.HTTP_200_OK)

def patch_users_me_password(
    data: PasswordChangeRequest,
    current= Depends(get_current_user),
    hasher=Depends(get_password_hasher),
    db: Session= Depends(get_db)
):
    return change_password(current,data,hasher,db)




@router.post("/forgot-password", response_model=MessageResponse, status_code=status.HTTP_200_OK)
def request_password_reset(
    data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    mailer = Depends(get_mailer)
):
    # Note: 'hasher' is not needed here as we aren't handling passwords directly
    return forgot_password(db, data, background_tasks, mailer)


@router.post("/reset-password", response_model=MessageResponse, status_code=status.HTTP_200_OK)
def perform_password_reset(
    data: ResetPasswordRequest,
    db: Session = Depends(get_db),
    hasher = Depends(get_password_hasher)
):
    return reset_password(db, data, hasher)


@router.get("/google/login", tags=["Auth"])
def google_login_start():
    """
    Redirects the user's browser to Google's consent screen.
    """
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI, # The backend callback
        "response_type": "code",
        "scope": "openid email profile",
    })
    return RedirectResponse(auth_url)

# --- NEW ROUTE TO HANDLE THE GOOGLE CALLBACK ---
@router.get("/google/callback", tags=["Auth"])
def google_login_callback(
    code: str,
    response: Response,
    db: Session = Depends(get_db),
    hasher = Depends(get_password_hasher)
):
    """
    Handles the redirect from Google, completes the login, sets a secure cookie,
    and redirects the user back to the frontend.
    """
    user, tokens = handle_google_login(db, code, hasher)
    
    # 2. First, create the RedirectResponse object that we will ultimately send.
    #    This is our "envelope."
    redirect_response = RedirectResponse(url=f"{settings.FRONTEND_URL}/auth/callback")
    
    # 3. Now, put the cookie directly into that specific envelope.
    set_refresh_cookie(redirect_response, tokens.refresh_token)
    
    # 4. Return the modified envelope. It now contains both the redirect
    #    location AND the Set-Cookie header.
    return redirect_response


