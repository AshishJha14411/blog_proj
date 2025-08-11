# app/schemas/stories.py
from pydantic import BaseModel, HttpUrl
from typing import Optional, Literal

class StoryGenerateIn(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None        # short description/blurb the user writes
    prompt: str                          # theme/instructions
    genre: Optional[str] = None
    tone: Optional[str] = None
    length_label: Optional[Literal["flash","short","medium","long"]] = None
    cover_image_url: Optional[HttpUrl] = None
    publish_now: bool = False
    temperature: Optional[float] = 0.8
    model_name: Optional[str] = "gpt-4o-mini"

class StoryFeedbackIn(BaseModel):
    feedback: str
