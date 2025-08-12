from pydantic import BaseModel, HttpUrl
from typing import Optional, List
from datetime import datetime

class AdCreate(BaseModel):
    advertiser_name: Optional[str] = None
    ad_content: Optional[str] = None
    image_url: Optional[HttpUrl] = None
    destination_url: HttpUrl
    slot: str
    tags: Optional[str] = None
    weight: int = 1
    active: bool = True
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None

class AdUpdate(BaseModel):
    advertiser_name: Optional[str] = None
    ad_content: Optional[str] = None
    image_url: Optional[HttpUrl] = None
    destination_url: Optional[HttpUrl] = None
    slot: Optional[str] = None
    tags: Optional[str] = None
    weight: Optional[int] = None
    active: Optional[bool] = None
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None

class AdOut(BaseModel):
    id: int
    advertiser_name: Optional[str]
    ad_content: Optional[str]
    image_url: Optional[str]
    destination_url: str
    slot: str
    tags: Optional[str]
    weight: int
    active: bool
    start_at: Optional[datetime]
    end_at: Optional[datetime]
    utm_source: Optional[str]
    utm_medium: Optional[str]
    utm_campaign: Optional[str]
    created_at: datetime
    updated_at: datetime
    class Config: from_attributes = True

class ServeAdOut(BaseModel):
    id: int
    advertiser_name: Optional[str]
    ad_content: Optional[str]
    image_url: Optional[str]
    destination_url: str
    slot: str

class AdList(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[AdOut]
