from pydantic import BaseModel, Field, constr
from typing import List, Optional
from datetime import datetime


# Hard cap prevents someone from posting a 10 MB comment; strip-whitespace +
# min_length blocks accidental empty submissions from the UI.
CommentContent = constr(strip_whitespace=True, min_length=1, max_length=5000)


class CommentCreate(BaseModel):
    content: CommentContent

class CommentAuthorOut(BaseModel):
    # Public-facing author shape: never expose email or other PII here —
    # this schema is served on unauthenticated endpoints.
    id: str
    username: str
    profile_image_url: Optional[str] = None
    class Config:
        from_attributes = True

class CommentOut(BaseModel):
    id: str
    user_id: str
    post_id: str
    content: str
    created_at: datetime
    user: CommentAuthorOut
    class Config:
        from_attributes = True

class CommentList(BaseModel):
    total: int
    items: List[CommentOut]
