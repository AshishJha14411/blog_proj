from pydantic import BaseModel
from typing import List
from datetime import datetime

class CommentCreate(BaseModel):
    content: str

class CommentOut(BaseModel):
    id: int
    user_id: int
    post_id: int
    content: str
    created_at: datetime

    class Config:
        orm_mode = True

class CommentList(BaseModel):
    total: int
    items: List[CommentOut]
