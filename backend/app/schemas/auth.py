from pydantic import BaseModel, EmailStr, constr, Field
from typing import Optional
import uuid


# Reused across signup/update — usernames and bios should have concrete caps
# so the DB never sees megabyte-sized inputs.
UsernameStr = constr(strip_whitespace=True, min_length=3, max_length=50)
PasswordStr = constr(min_length=8, max_length=128)
BioStr = constr(max_length=500)


class SignUpRequest(BaseModel):
    email: EmailStr
    username: UsernameStr
    password: PasswordStr
    profile_image_url: Optional[constr(max_length=2048)] = None
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
    username: UsernameStr
    password: PasswordStr

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
    profile_image_url: Optional[constr(max_length=2048)] = None
    bio: Optional[BioStr] = None
    social_links: Optional[dict] = None

class PasswordChangeRequest(BaseModel):
    old_password: PasswordStr
    new_password: PasswordStr

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: constr(min_length=10, max_length=256)
    new_password: PasswordStr
    
class GoogleLoginRequest(BaseModel):
    code: str  
    
class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: UserProfile