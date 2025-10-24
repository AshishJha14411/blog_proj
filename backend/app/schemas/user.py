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

    # --- THIS IS THE MAGIC ---
    # We teach Pydantic how to handle the translation to JSON.
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            # Tell Pydantic: "When you find a UUID object,
            # use the str() function to convert it for JSON."
            uuid.UUID: str
        }
    )
class UserSummary(BaseModel):
    id: uuid.UUID
    username: str
