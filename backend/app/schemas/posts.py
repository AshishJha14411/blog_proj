from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional
from datetime import datetime
from app.schemas.user import UserOut
class PostCreate(BaseModel):
    title: str
    header: Optional[str] = None
    content: str
    cover_image_url: Optional[HttpUrl] = None
    tags: List[str] = []
    is_published: bool = True

class PostUpdate(BaseModel):
    title: Optional[str] = None
    header: Optional[str] = None
    content: Optional[str] = None
    cover_image_url: Optional[HttpUrl] = None
    tags: Optional[List[str]] = None
    is_published: Optional[bool] = None

class TagOut(BaseModel):
    name: str
    class Config:
        orm_mode = True

class PostOut(BaseModel):
    id: int
    title: str
    header: Optional[str]
    content: str
    cover_image_url: Optional[HttpUrl]
    user_id: int 
    user: UserOut 
    tags: List[TagOut]
    is_published: bool
    created_at: datetime
    updated_at: datetime
    
    is_liked_by_user: bool = Field(False)
    is_bookmarked_by_user: bool = Field(False)

    class Config:
        orm_mode = True

class PostList(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[PostOut]

    class Config:
        from_attributes = True # or orm_mode = True
