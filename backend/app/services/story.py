from __future__ import annotations
from app.utils.time import utcnow
from datetime import datetime
from typing import List, Optional, Tuple
import uuid
from fastapi import HTTPException, status, Request
from sqlalchemy.orm import Session, joinedload, selectinload
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
from app.tasks.moderation import moderate_story_task
# Initialize the LLM Adapter once
_llm = LLMAdapter()

# WHY: soft-deleted (is_disabled) authors keep their non-flagged stories —
# User.stories has no delete-orphan cascade (see models/user.py) — but the
# byline shouldn't keep advertising a deleted account's real username.
DELETED_USER_LABEL = "Deleted User"


def _mask_deleted_authors(items: List[Story]) -> None:
    """In-memory-only username override for disabled authors.

    Mutates the loaded ORM `User.username` attribute for display, same
    pattern as `_populate_interaction_flags` below — never committed, so it
    can't leak into the database.
    """
    for item in items:
        if item.user is not None and item.user.is_disabled:
            item.user.username = DELETED_USER_LABEL


# /** WHY: AI moderation used to run inline and add LLM latency to every
#     publish. Now the row lands in `pending`, the async task runs the
#     moderator, and the row flips to `published` / `rejected` when it's
#     done. Publish latency drops to a DB insert. **/
# /** WHY-THIS-WAY: enqueue via .delay() — eager-mode in tests, real Redis
#     queue in prod. Under eager mode the transition happens synchronously
#     right after the request commits, so integration tests still see the
#     final state without special-casing. **/
def create_story(db: Session, data: StoryCreate, current_user: User) -> Story:
    tag_objs = []
    allowed_roles = {"creator", "moderator", "superadmin"}
    if current_user.role.name not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to create a story."
        )
    for name in dict.fromkeys(data.tag_names or []):
        tag = db.query(Tag).filter(Tag.name == name).first()
        if not tag:
            tag = Tag(name=name)
            db.add(tag)
            db.flush()
        tag_objs.append(tag)

    # /** WHY: land the row as `pending` regardless of the client-requested
    #     `is_published` — the moderation task decides whether it's published
    #     or rejected. A user can no longer publish unmoderated content by
    #     racing an upload with a flagged content check. **/
    wants_publish = bool(data.is_published)

    new_story = Story(
        user_id=str(current_user.id),
        title=data.title,
        header=data.header,
        content=data.content,
        cover_image_url=str(data.cover_image_url) if data.cover_image_url else None,
        is_published=False,       # stays False until moderation approves
        is_flagged=False,
        flag_source="none",
        source=ContentSource.user,
        status=StoryStatus.pending if wants_publish else StoryStatus.draft,
    )
    new_story.tags = tag_objs
    db.add(new_story)
    db.flush()  # get new_story.id

    story_id = str(new_story.id)
    db.commit()
    db.refresh(new_story)

    if wants_publish:
        # Only enqueue when the author actually wants this published. Drafts
        # skip moderation until the publish action is invoked separately.
        moderate_story_task.delay(story_id=story_id)

    return new_story

# --- STORY CREATION (AI) ---
def generate_story(db: Session, data: StoryGenerateIn, current_user: User) -> Story:
    
    allowed_roles = {"creator", "moderator", "superadmin"}
    if current_user.role.name not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to create a story."
        )
    
    full_prompt = _build_story_prompt(
        user_prompt=data.prompt,
        genre=data.genre,
        tone=data.tone,
        length_label=data.length_label
    )
    # The LLM call itself stays inline — it IS the request's purpose and can't
    # be deferred. Only moderation is deferred, to match create_story's flow.
    story_text, msg_id = _generate_story_text(prompt=full_prompt, model=data.model_name, temperature=data.temperature)
    return finalize_generated_story(db, data, current_user, story_text=story_text, msg_id=msg_id)


def build_generation_prompt(data: StoryGenerateIn) -> str:
    """Public wrapper so the streaming route can reuse the prompt builder."""
    return _build_story_prompt(
        user_prompt=data.prompt, genre=data.genre, tone=data.tone, length_label=data.length_label
    )


def finalize_generated_story(
    db: Session, data: StoryGenerateIn, current_user: User, *, story_text: str, msg_id: str
) -> Story:
    """Persist a generated story + its first revision, then enqueue moderation.

    Shared by both the synchronous `generate_story` and the streaming route
    (`/stories/generate/stream`) so the landing rules stay in one place.

    /** WHY: unified moderation flow with create_story. Land as `pending`
        when the author wants it published, then the async task runs the same
        moderate_content() check and flips to published/rejected. Non-publish
        generations rest as `generated` (the AI equivalent of a human draft)
        and skip moderation until publish is invoked. **/
    """
    title = data.title or _default_title_from(story_text)

    new_story = Story(
        user_id=str(current_user.id), title=title, header=data.summary, content=story_text,
        cover_image_url=str(data.cover_image_url) if data.cover_image_url else None,
        is_published=False,          # stays False until moderation approves
        is_flagged=False, flag_source="none",
        source=ContentSource.ai, genre=data.genre, tone=data.tone,
        length_label=LengthLabel(data.length_label) if data.length_label else None,
        summary=data.summary, words_count=_count_words(story_text),
        status=(StoryStatus.pending if data.publish_now else StoryStatus.generated),
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

    story_id = str(new_story.id)
    db.commit()
    db.refresh(new_story)

    if data.publish_now:
        moderate_story_task.delay(story_id=story_id)

    return new_story

# --- READING STORIES ---
def _populate_interaction_flags(
    db: Session,
    items: List[Story],
    current_user: Optional[User],
) -> None:
    """Batch-load like/bookmark flags for a page of stories: 2 queries, not 2N."""
    if not current_user or not items:
        for s in items:
            s.is_liked_by_user = False
            s.is_bookmarked_by_user = False
        return

    story_ids = [s.id for s in items]
    liked = {
        sid for (sid,) in db.query(Like.story_id).filter(
            Like.user_id == current_user.id,
            Like.story_id.in_(story_ids),
        )
    }
    marked = {
        sid for (sid,) in db.query(Bookmark.story_id).filter(
            Bookmark.user_id == current_user.id,
            Bookmark.story_id.in_(story_ids),
        )
    }
    for s in items:
        s.is_liked_by_user = s.id in liked
        s.is_bookmarked_by_user = s.id in marked


def get_all_stories(db: Session, limit: int, offset: int, tag: Optional[str], author_id: Optional[uuid.UUID], current_user: Optional[User]) -> Tuple[int, List[Story]]:
    # W7: eager-load user + tags so `StoryOut.model_validate(item)` doesn't lazy-load per row.
    query = (
        db.query(Story)
        .options(joinedload(Story.user), selectinload(Story.tags))
        .filter(Story.deleted_at.is_(None))
    )
    is_mod = bool(current_user and current_user.role.name in ("moderator", "superadmin"))
    if not is_mod:
        # /** WHY: `pending` and `rejected` rows must never show up in the
        #     public list, even before the moderation task finishes running.
        #     is_published=True is the strongest single filter. **/
        query = query.filter(Story.is_published == True)
    if author_id:
        query = query.filter(Story.user_id == author_id)
    if tag:
        query = query.join(Story.tags).filter(Tag.name == tag)

    total = query.count()
    items = query.order_by(Story.created_at.desc()).offset(offset).limit(limit).all()
    _populate_interaction_flags(db, items, current_user)
    _mask_deleted_authors(items)
    return total, items

def get_user_stories(db: Session, user: User, limit: int, offset: int) -> Tuple[int, List[Story]]:
    query = (
        db.query(Story)
        .options(joinedload(Story.user), selectinload(Story.tags))
        .filter(Story.user_id == user.id, Story.deleted_at.is_(None))
    )
    total = query.count()
    items = query.order_by(Story.created_at.desc()).offset(offset).limit(limit).all()
    _populate_interaction_flags(db, items, user)
    return total, items

def get_story_details(db: Session, story_id: uuid.UUID, current_user: Optional[User], request: Request) -> Story:
    story = (
        db.query(Story)
        .options(joinedload(Story.user), selectinload(Story.tags))
        .filter(Story.id == story_id, Story.deleted_at.is_(None))
        .first()
    )
    if not story:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Story not found")

    if not story.is_published and not (current_user and (story.user_id == current_user.id or current_user.role.name in ("moderator", "superadmin"))):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Story not found")

    # W7: like/bookmark flags — run each query once, not twice.
    if current_user:
        story.is_liked_by_user = db.query(Like).filter_by(user_id=current_user.id, story_id=story.id).first() is not None
        story.is_bookmarked_by_user = db.query(Bookmark).filter_by(user_id=current_user.id, story_id=story.id).first() is not None
    else:
        story.is_liked_by_user = False
        story.is_bookmarked_by_user = False

    # Log the view
    db.add(ViewHistory(
        story_id=story.id, user_id=current_user.id if current_user else None,
        ip_address=request.client.host, user_agent=request.headers.get("user-agent")
    ))
    db.commit()

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
        is_liked_by_user=bool(getattr(story, "is_liked_by_user", False)),
        is_bookmarked_by_user=bool(getattr(story, "is_bookmarked_by_user", False)),
        user=UserSummary(
            id=str(story.user.id),
            username=DELETED_USER_LABEL if story.user.is_disabled else story.user.username
        ))

# --- MODIFYING STORIES ---
def update_story(db: Session, story_id: uuid.UUID, data: StoryUpdate, current_user: User) -> Story:
    story = db.get(Story, story_id)
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

            # ✅ FIX: assign automod user ID instead of None
            automod_user = get_automod_user(db)
            db.add(Flag(
                flagged_by_user_id=automod_user.id,
                story_id=story.id,
                reason="; ".join(cats) or "Profanity detected on update",
                status="open"
            ))


    story.updated_at = utcnow()
    db.commit()
    db.refresh(story)
    return story

def delete_story(db: Session, story_id: uuid.UUID, current_user: User) -> None:
    story = db.get(Story, story_id)
    if not story:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Story not found")
    _ensure_authorization(story, current_user)
    
    story.deleted_at = utcnow()
    db.commit()
    return {"message": "Story deleted successfully"}

# --- AI-SPECIFIC MODIFICATIONS ---
def regenerate_with_feedback(db: Session, story_id: uuid.UUID, feedback: str, current_user: User) -> Story:
    story = db.get(Story, story_id)
    if not story:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Story not found")
    _ensure_authorization(story, current_user)

    regen_prompt = _build_regen_prompt(base_prompt=story.prompt or "", feedback=feedback)
    new_text, msg_id = _generate_story_text(prompt=regen_prompt, model=story.model_name, temperature=story.temperature)
    flagged, cats = moderate_content([story.title, new_text])

    story.version += 1
    story.content = new_text
    story.words_count = _count_words(new_text)
    story.updated_at = utcnow()
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
    story = db.get(Story, story_id)
    if not story:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Story not found")
    _ensure_authorization(story, current_user)
    if story.is_flagged:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Story is flagged and cannot be published.")

    story.is_published = True
    story.status = StoryStatus.published
    story.updated_at = utcnow()
    db.commit()
    db.refresh(story)
    return story

def unpublish_story(db: Session, story_id: uuid.UUID, current_user: User) -> Story:
    story = db.get(Story, story_id)
    if not story:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Story not found")
    _ensure_authorization(story, current_user)

    story.is_published = False
    story.status = StoryStatus.generated
    story.updated_at = utcnow()
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

# Concrete word-count targets per length label. Without these the model has
# no idea what "long" means and defaults to a few lines. "at least" framing
# (rather than a capped range) pushes it to actually fill the length out.
_LENGTH_GUIDANCE = {
    "flash": "a flash fiction piece of roughly 300–600 words",
    "short": "a short story of at least 1,000 words (roughly 1,000–1,800)",
    "medium": "a substantial story of at least 2,500 words (roughly 2,500–4,000)",
    "long": "a long, fully-developed story of at least 4,000 words — do not cut it short; "
            "expand scenes, dialogue, and description until it genuinely reads as a long piece",
}


def _build_story_prompt(user_prompt: str, genre: str|None, tone: str|None, length_label: str|None) -> str:
    length_target = _LENGTH_GUIDANCE.get((length_label or "short"), _LENGTH_GUIDANCE["short"])
    return f"""
You are a skilled fiction writer. Write {length_target}, based on the instructions below.

Write the FULL story — a beginning, a developed middle, and an ending. Do not
summarize or write an outline. Do not stop early. Keep writing until the story
is complete at the target length.

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
- Target length: {length_target}

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
