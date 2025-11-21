from passlib.context import CryptContext
from jose import jwt # Assuming python-jose for jwt
from datetime import datetime, timedelta , timezone
from app.core.config import settings
import uuid
from typing import Optional # Add Optional import

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256" # Define the algorithm once

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# JWT token utilities
def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc), # Issued At time
        "jti": str(uuid.uuid4()), # Add a unique JWT ID
        "type": "access" # Clarify token type
    })
    
    # --- SECURITY FIX: Use the dedicated JWT_SECRET_KEY ---
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=ALGORITHM)
    # --- END FIX ---

def create_refresh_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(days=14))
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "jti": str(uuid.uuid4()), # Add a unique JWT ID to the refresh token
        "type": "refresh"
    })
    
    # --- SECURITY FIX: Use the dedicated JWT_SECRET_KEY ---
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=ALGORITHM)
    # --- END FIX ---


def decode_access_token(token: str) -> dict:
    """
    Decodes a token using the dedicated JWT secret key.
    (Note: This function replaces the redundant second definition.)
    """
    # --- SECURITY FIX: Use the dedicated JWT_SECRET_KEY ---
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[ALGORITHM])
    # --- END FIX ---