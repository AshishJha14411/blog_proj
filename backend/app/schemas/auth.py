from pydantic import BaseModel, EmailStr, constr
from typing import Optional
import uuid
class SignUpRequest(BaseModel):
    email: EmailStr
    username: str
    password: str
    profile_image_url: Optional[str] = None
    social_links: Optional[dict] = None

class SignUpResponse(BaseModel):
    id: str
    email: EmailStr
    username: str
    message: str

class RoleOut(BaseModel):
    id: uuid.UUID
    name: str
    class Config:
        from_attributes = True
# ------------LOGIN------------- #
class LoginRequest(BaseModel):
    username: constr(min_length=3)
    password: constr(min_length=8)

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class MessageResponse(BaseModel):
    message: str

class VerifyOtpRequest(BaseModel):
    email: EmailStr
    otp_code: constr(min_length=6, max_length=6)
    
class UserProfile(BaseModel):
    id: uuid.UUID
    email: EmailStr
    username: str
    is_verified: bool
    profile_image_url: Optional[str]
    social_links: Optional[dict]
    total_posts: int
    bio: Optional[str] = None
    total_likes: int
    total_comments: int
    role: RoleOut
    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    profile_image_url: Optional[str] = None
    bio: Optional[str] = None
    social_links: Optional[dict] = None

class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: constr(min_length=8)
    
class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: constr(min_length=8)
    
class GoogleLoginRequest(BaseModel):
    code: str  
    
class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: UserProfile