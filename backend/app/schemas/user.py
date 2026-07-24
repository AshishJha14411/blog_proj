# In app/schemas/users.py (or a similar file)
from pydantic import BaseModel, ConfigDict
from typing import Optional
import uuid

# This is the schema used for most user-related API responses.
class UserOut(BaseModel):
    # We define the fields with their "correct" Python types.
    id: uuid.UUID
    username: str
    email: str
    profile_image_url: Optional[str] = None
    bio: Optional[str] = None
    # ... add any other fields you want to expose

    # Pydantic v2 serializes UUIDs to strings in JSON mode natively, so no
    # json_encoders needed (it's deprecated and slated for removal in v3).
    model_config = ConfigDict(from_attributes=True)
class UserSummary(BaseModel):
    id: uuid.UUID
    username: str
