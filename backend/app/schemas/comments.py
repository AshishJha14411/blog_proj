from pydantic import BaseModel
from typing import List
from datetime import datetime
from app.schemas.user import UserOut
class CommentCreate(BaseModel):
    content: str

class CommentOut(BaseModel):
    id: str
    user_id: str
    post_id: str
    content: str
    created_at: datetime
    user: UserOut
    class Config:
        orm_mode = True
        from_attributes = True

class CommentList(BaseModel):
    total: int
    items: List[CommentOut]
