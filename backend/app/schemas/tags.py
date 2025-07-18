from pydantic import BaseModel, Field
from typing import Optional, List

class TagBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=255)

class TagCreate(TagBase):
    pass

class TagUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=255)

class TagOut(TagBase):
    id: int

    class Config:
        # Pydantic v2: use from_attributes instead of orm_mode
        from_attributes = True

class TagList(BaseModel):
    tags: List[TagOut]
