from __future__ import annotations
from datetime import datetime
from typing import List, Optional, Tuple
import uuid
from fastapi import HTTPException, status, Request
from sqlalchemy.orm import Session , joinedload
# Import all necessary models
from app.models.like import Like
from app.models.bookmarks import Bookmark
from app.models.stories import Story, ContentSource, StoryStatus, LengthLabel
from app.models.tags import Tag
from app.models.view_history import ViewHistory
from app.models.user import User
from app.models.flag import Flag
from app.models.story_revision import StoryRevision
# Import all necessary schemas
from app.schemas.stories import StoryCreate, StoryUpdate, StoryGenerateIn, StoryFeedbackIn, StoryOut, TagSummary, UserSummary
from app.services.moderation import moderate_content
from app.llm.adapter import LLMAdapter
from app.core.config import settings
from app.services.system import get_automod_user 
# Initialize the LLM Adapter once
_llm = LLMAdapter()
# --- STORY CREATION (HUMAN) ---
def create_story(db: Session, data: StoryCreate, current_user: User) -> Story:
    tag_objs = []
    for name in data.tag_names: # Use tag_names from the unified schema
        tag = db.query(Tag).filter(Tag.name == name).first()
        if not tag:
            tag = Tag(name=name)
            db.add(tag)
            db.flush()
        tag_objs.append(tag)
        
    # Profanity check
    flagged, cats = moderate_content([data.title, data.content])
    
    new_story = Story(
        user_id=str(current_user.id),
        title=data.title,
        header=data.header,
        content=data.content,
        cover_image_url=str(data.cover_image_url) if data.cover_image_url else None,
        is_published=(data.is_published and not flagged),
        is_flagged=flagged,
        flag_source="ai" if flagged else "none",
        source=ContentSource.user,
        status=StoryStatus.published if (data.is_published and not flagged) else StoryStatus.draft
    )
    new_story.tags = tag_objs
    db.add(new_story)
    db.flush() # Flush to get the new_story.id

    if flagged:
        # Use None for system-generated flags, not a hardcoded user ID
        automod_user = get_automod_user(db)
        flag = Flag(
            flagged_by_user_id=automod_user.id,
            story_id=str(new_story.id),
            reason="; ".join(cats) or "Profanity detected by AI",
            status="open"
        )
        db.add(flag)
        
    db.commit()
    db.refresh(new_story)
    return new_story

# --- STORY CREATION (AI) ---
def generate_story(db: Session, data: StoryGenerateIn, current_user: User) -> Story:
    full_prompt = _build_story_prompt(
        user_prompt=data.prompt,
        genre=data.genre,
        tone=data.tone,
        length_label=data.length_label
    )
    story_text, msg_id = _generate_story_text(prompt=full_prompt, model=data.model_name, temperature=data.temperature)
    title = data.title or _default_title_from(story_text)
    flagged, cats = moderate_content([title, story_text])

    new_story = Story(
        user_id=str(current_user.id), title=title, header=data.summary, content=story_text,
        cover_image_url=str(data.cover_image_url) if data.cover_image_url else None,
        is_published=(data.publish_now and not flagged),
        is_flagged=flagged, flag_source="ai" if flagged else "none",
        source=ContentSource.ai, genre=data.genre, tone=data.tone,
        length_label=LengthLabel(data.length_label) if data.length_label else None,
        summary=data.summary, words_count=_count_words(story_text),
        status=(StoryStatus.published if (data.publish_now and not flagged) else StoryStatus.generated),
        prompt=data.prompt, model_name=data.model_name, temperature=data.temperature,
        provider_message_id=msg_id, version=1
    )
    db.add(new_story)
    db.flush() 

    # Create the first revision record
    db.add(StoryRevision(
        stories_id=str(new_story.id), version=1, content=story_text, prompt=data.prompt,
        model_name=new_story.model_name, provider_message_id=msg_id, user_id=current_user.id
    ))

    db.commit()
    db.refresh(new_story)
    return new_story

# --- READING STORIES ---
def get_all_stories(db: Session, limit: int, offset: int, tag: Optional[str], author_id: Optional[uuid.UUID], current_user: Optional[User]) -> Tuple[int, List[Story]]:
    query = db.query(Story).filter(Story.deleted_at == None)
    if not (current_user and current_user.role.name in ("moderator", "superadmin")):
        query = query.filter(Story.is_published == True)
    if author_id:
        query = query.filter(Story.user_id == author_id)
    if tag:
        query = query.join(Story.tags).filter(Tag.name == tag)
        
    total = query.count()
    items = query.order_by(Story.created_at.desc()).offset(offset).limit(limit).all()
    return total, items

def get_user_stories(db: Session, user: User, limit: int, offset: int) -> Tuple[int, List[Story]]:
    query = db.query(Story).filter(Story.user_id == user.id, Story.deleted_at == None)
    total = query.count()
    items = query.order_by(Story.created_at.desc()).offset(offset).limit(limit).all()
    return total, items

def get_story_details(db: Session, story_id: uuid.UUID, current_user: Optional[User], request: Request) -> Story:
    story = db.query(Story).options(joinedload(Story.tags)).filter(Story.id == story_id, Story.deleted_at == None).first()
    if not story:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Story not found")
    
    if not story.is_published and not (current_user and (story.user_id == current_user.id or current_user.role.name in ("moderator", "superadmin"))):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Story not found")
        
    # Log the view
    db.add(ViewHistory(
        story_id=story.id, user_id=current_user.id if current_user else None,
        ip_address=request.client.host, user_agent=request.headers.get("user-agent")
    ))
    db.commit()

    # Dynamically set like/bookmark status for the response schema
    if current_user:
        story.is_liked_by_user = db.query(Like).filter_by(user_id=current_user.id, story_id=story.id).first() is not None
        story.is_bookmarked_by_user = db.query(Bookmark).filter_by(user_id=current_user.id, story_id=story.id).first() is not None
    else:
        story.is_liked_by_user = False
        story.is_bookmarked_by_user = False
        
    return StoryOut(
        id=str(story.id),
        title=story.title,
        content=story.content,
        user_id=str(story.user_id),
        created_at=story.created_at,
        updated_at=story.updated_at,
        header=story.header,
        cover_image_url=story.cover_image_url,
        is_published=story.is_published,
        source=story.source,
        tags=[TagSummary(id=str(tag.id), name=tag.name) for tag in story.tags],
        # Explicitly build the nested UserSummary, converting its ID.
        user=UserSummary(
            id=str(story.user.id),
            username=story.user.username
        ))

# --- MODIFYING STORIES ---
def update_story(db: Session, story_id: uuid.UUID, data: StoryUpdate, current_user: User) -> Story:
    story = db.query(Story).get(story_id)
    if not story:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Story not found")
    _ensure_authorization(story, current_user)

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(story, field, value)

    if any(f in ("title", "content") for f in update_data):
        flagged, cats = moderate_content([story.title, story.content])
        if flagged:
            story.is_flagged = True
            story.flag_source = "ai"
            story.is_published = False
            db.add(Flag(
                flagged_by_user_id=None, story_id=story.id,
                reason="; ".join(cats) or "Profanity detected on update", status="open"
            ))

    story.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(story)
    return story

def delete_story(db: Session, story_id: uuid.UUID, current_user: User) -> None:
    story = db.query(Story).get(story_id)
    if not story:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Story not found")
    _ensure_authorization(story, current_user)
    
    story.deleted_at = datetime.utcnow()
    db.commit()

# --- AI-SPECIFIC MODIFICATIONS ---
def regenerate_with_feedback(db: Session, story_id: uuid.UUID, feedback: str, current_user: User) -> Story:
    story = db.query(Story).get(story_id)
    if not story:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Story not found")
    _ensure_authorization(story, current_user)

    regen_prompt = _build_regen_prompt(base_prompt=story.prompt or "", feedback=feedback)
    new_text, msg_id = _generate_story_text(prompt=regen_prompt, model=story.model_name, temperature=story.temperature)
    flagged, cats = moderate_content([story.title, new_text])

    story.version += 1
    story.content = new_text
    story.words_count = _count_words(new_text)
    story.updated_at = datetime.utcnow()
    story.last_feedback = feedback
    story.is_flagged = flagged
    story.is_published = False
    story.status = StoryStatus.generated

    db.add(StoryRevision(
        stories_id=story.id, version=story.version, content=new_text, prompt=regen_prompt,
        feedback=feedback, model_name=story.model_name, provider_message_id=msg_id, user_id=current_user.id
    ))
    db.commit()
    db.refresh(story)
    return story

def publish_story(db: Session, story_id: uuid.UUID, current_user: User) -> Story:
    story = db.query(Story).get(story_id)
    if not story:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Story not found")
    _ensure_authorization(story, current_user)
    if story.is_flagged:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Story is flagged and cannot be published.")

    story.is_published = True
    story.status = StoryStatus.published
    story.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(story)
    return story

def unpublish_story(db: Session, story_id: uuid.UUID, current_user: User) -> Story:
    story = db.query(Story).get(story_id)
    if not story:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Story not found")
    _ensure_authorization(story, current_user)

    story.is_published = False
    story.status = StoryStatus.generated
    story.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(story)
    return story

# --- HELPER FUNCTIONS ---
def _ensure_authorization(post: Story, user: User):
    if (post.user_id != user.id) and (user.role.name not in ("moderator", "superadmin")):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not authorized for this post")

def _generate_story_text(*, prompt: str, model: str, temperature: float) -> Tuple[str, str]:
    text, msg_id = _llm.generate(
        prompt,
        model=model,
        temperature=temperature,
        max_tokens=settings.LLM_MAX_TOKENS,
        timeout=settings.LLM_TIMEOUT,
    )
    if not text.strip():
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail="LLM returned empty text")
    return text, msg_id

def _build_story_prompt(user_prompt: str, genre: str|None, tone: str|None, length_label: str|None) -> str:
    return f"""
You are a skilled fiction writer. Write a complete short story based on the instructions below.

Output STRICTLY valid, minimal HTML. Use:
- <h1> for the title (if you invent one)
- <p> for paragraphs (no extra CSS)
- <em> for whispers or inner thoughts
- Use explicit line breaks with <br/> only inside poems/notes
- When a sound effect occurs, insert a bracketed cue like [SFX: door slam]
- Do NOT include <html>, <head>, or <body> tags. Only the story fragment HTML.

Constraints:
- Genre: {genre or "any"}
- Tone: {tone or "any"}
- Length: {length_label or "short"} (aim within that range)
- Keep it readable on web; short paragraphs.

Instructions/theme:
{user_prompt}
""".strip()

def _build_regen_prompt(base_prompt: str, feedback: str) -> str:
    return (
        "Revise the following short story per the reader feedback.\n\n"
        "Guidelines:\n"
        "- Preserve the core idea and characters.\n"
        "- Improve pacing and clarity.\n"
        "- Keep the same length range.\n"
        "- Avoid explicit sexual content, hate speech, and graphic violence.\n\n"
        f"Original instructions/context:\n{base_prompt}\n\n"
        f"Reader feedback to address:\n{feedback}\n\n"
        "Return only the revised story text, no commentary."
    )

def _default_title_from(story_text: str, fallback: str = "Untitled Story") -> str:
    line = (story_text or "").strip().splitlines()[0].strip()
    if 5 <= len(line) <= 80:
        return line
    return fallback

def _count_words(text: str) -> int:
    return len((text or "").split())
