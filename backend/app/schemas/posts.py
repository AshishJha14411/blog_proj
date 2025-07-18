from pydantic import BaseModel, HttpUrl
from typing import List, Optional
from datetime import datetime

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
    author_id: int
    tags: List[TagOut]
    is_published: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class PostList(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[PostOut]
