from fastapi import APIRouter, Depends, status, Query, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import json
import logging
import uuid

logger = logging.getLogger("app")

# Import all dependencies and the unified schemas/services
from app.dependencies import (
    get_db, get_current_user_optional, get_current_user,
    get_async_db, get_current_user_optional_async, get_current_user_async,
)
from app.authz import Perm, require
from app.models.user import User
from app.schemas.stories import StoryCreate, StoryUpdate, StoryOut, StoryList, UserSummary, TagSummary, StoryGenerateIn, StoryFeedbackIn
from app.services import story
from app.utils.rate_limiter import story_create_rate_limiter, llm_generate_rate_limiter
from app.utils import cache as story_cache
from app.utils.http_cache import conditional_model_response

# --- UNIFIED ROUTER ---
router = APIRouter(prefix="/stories", tags=["Stories"])

# Shared gate instance so tests can override this exact object.
can_create_story = require(Perm.STORY_CREATE)


# --- HUMAN-WRITTEN STORY ENDPOINTS ---

@router.post(
    "/",
    response_model=StoryOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(story_create_rate_limiter)],
)
def create_new_story(
    data: StoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(can_create_story)
):
    """Creates a new story written by a user."""
    new_story = story.create_story(db, data, current_user)
    # Cache-aside invalidation: nuke every cached list page + this story's
    # detail so the next read repopulates. Cheaper than trying to patch.
    story_cache.invalidate_story(str(new_story.id))

    # Manually build the response to ensure all fields and types are correct
    return StoryOut(
        id=str(new_story.id),
        title=new_story.title,
        content=new_story.content,
        user_id=str(new_story.user_id),
        created_at=new_story.created_at,
        updated_at=new_story.updated_at,
        header=new_story.header,
        cover_image_url=new_story.cover_image_url,
        is_published=new_story.is_published,
        status=new_story.status,
        source=new_story.source,
        # user=UserSummary.from_orm(new_story.user),
        tags=[
            TagSummary(id=str(tag.id), name=tag.name) for tag in new_story.tags
        ],
        
        
        user=UserSummary(
            id=str(new_story.user.id),
            username=new_story.user.username
        ),
    )

@router.get("/", response_model=StoryList, status_code=status.HTTP_200_OK)
async def list_all_stories(
    request: Request,
    http_response: Response,
    limit: int = Query(10, gt=0, le=100),
    offset: int = Query(0, ge=0),
    cursor: Optional[str] = Query(None, description="Keyset cursor from a prior page's next_cursor"),
    tag: Optional[str] = Query(None),
    author_id: Optional[uuid.UUID] = Query(None), # Correctly a UUID
    db: AsyncSession = Depends(get_async_db),
    current_user: Optional[User] = Depends(get_current_user_optional_async)
):
    """Lists all stories, with filters. ASYNC.

    Two pagination modes:
    - Keyset (preferred): pass `?cursor=` (from a prior response's next_cursor)
      for O(1)-per-page depth. Uncached (cursor pages are rarely re-requested).
    - Offset (legacy): `?offset=`. Cached for anonymous callers.

    Cache: anon-only. Logged-in results include per-user like/bookmark flags
    so caching them would either leak state between users or require a
    per-user key. Invalidation happens on any story create/update/delete/publish.
    The cache layer is a sync Redis client; its calls are sub-millisecond local
    ops, so the brief event-loop block is an accepted trade vs. a second async
    Redis client.
    """
    # Keyset path — cursor supplied OR offset==0 first page requested as keyset.
    if cursor is not None:
        items, next_cursor = await story.get_stories_keyset(db, limit, cursor, tag, author_id, current_user)
        validated = [StoryOut.model_validate(i, from_attributes=True) for i in items]
        result = StoryList(total=len(validated), limit=limit, offset=0, items=validated, next_cursor=next_cursor)
        return conditional_model_response(request, http_response, result)

    can_cache = current_user is None
    viewer_key = "anon" if can_cache else f"u:{current_user.id}"
    key = story_cache.story_list_key(
        limit=limit,
        offset=offset,
        tag=tag,
        author_id=str(author_id) if author_id else None,
        viewer=viewer_key,
    )

    if can_cache:
        cached = story_cache.get_cached(key)
        if cached is not None:
            return conditional_model_response(request, http_response, StoryList.model_validate(cached))

    total, items = await story.get_all_stories(db, limit, offset, tag, author_id, current_user)
    validated_items = [StoryOut.model_validate(item, from_attributes=True) for item in items]
    result = StoryList(total=total, limit=limit, offset=offset, items=validated_items)

    if can_cache:
        story_cache.set_cached(key, result.model_dump(mode="json"), story_cache.STORY_LIST_TTL)

    return conditional_model_response(request, http_response, result)


@router.get("/search", response_model=StoryList, status_code=status.HTTP_200_OK)
async def search_stories(
    request: Request,
    response: Response,
    q: str = Query(..., min_length=1, description="Full-text search query"),
    limit: int = Query(10, gt=0, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_async_db),
    current_user: Optional[User] = Depends(get_current_user_optional_async),
):
    """Full-text search over published stories, ranked by relevance. ASYNC.

    Declared BEFORE `/{story_id}` so "search" isn't parsed as a UUID path.
    """
    total, items = await story.search_stories(db, q, limit, offset, current_user)
    validated_items = [StoryOut.model_validate(item, from_attributes=True) for item in items]
    result = StoryList(total=total, limit=limit, offset=offset, items=validated_items)
    return conditional_model_response(request, response, result)


@router.get("/me", response_model=StoryList, status_code=status.HTTP_200_OK)
async def list_my_stories(
    limit: int = Query(10, gt=0, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_async)
):
    """Lists all stories created by the current authenticated user. ASYNC."""
    total, items = await story.get_user_stories(db, current_user, limit, offset)
    validated_items = [
        StoryOut(
            id=str(story.id),
            title=story.title,
            content=story.content,
            user_id=str(story.user_id),
            created_at=story.created_at,
            updated_at=story.updated_at,
            header=story.header,
            cover_image_url=story.cover_image_url,
            is_published=story.is_published,
            status=story.status,
            source=story.source,
            genre=story.genre,
            tone=story.tone,
            length_label=story.length_label,
            summary=story.summary,
            user=UserSummary(id=str(story.user.id), username=story.user.username),
            tags=[TagSummary(id=str(tag.id), name=tag.name) for tag in story.tags],
            is_liked_by_user=getattr(story, 'is_liked_by_user', False),
            is_bookmarked_by_user=getattr(story, 'is_bookmarked_by_user', False)
        ) for story in items
    ]
    return StoryList(total=total, limit=limit, offset=offset, items=validated_items)


@router.get("/popular", response_model=List[StoryOut], status_code=status.HTTP_200_OK)
async def list_popular_stories(
    request: Request,
    response: Response,
    limit: int = Query(6, gt=0, le=24),
    days: Optional[int] = Query(
        None, ge=1, le=365,
        description="Restrict to stories published in the last N days. Omit for all-time.",
    ),
    db: AsyncSession = Depends(get_async_db),
    current_user: Optional[User] = Depends(get_current_user_optional_async),
):
    """Most-engaged published stories, ranked by likes + comments + bookmarks.

    Declared BEFORE `/{story_id}` so "popular" isn't parsed as a UUID path.

    Returns a bare list rather than a `StoryList` envelope: this powers a fixed
    home-page rail, not a paginated view, so a total/offset would be noise.
    Stories with no engagement are omitted, so an empty list is a valid answer
    and the client hides the section.
    """
    items = await story.get_popular_stories(db, limit, days, current_user)
    return [StoryOut.model_validate(item, from_attributes=True) for item in items]


@router.get("/{story_id}", response_model=StoryOut, status_code=status.HTTP_200_OK)
async def read_story_details(
    story_id: uuid.UUID, # Correctly a UUID
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_async_db),
    current_user: Optional[User] = Depends(get_current_user_optional_async)
):
    """Gets the full details of a single story. ASYNC — the service builds and
    returns the StoryOut directly (incl. deleted-author masking). Sends an ETag
    so a repeat request revalidates into a cheap 304 (see http_cache)."""
    result = await story.get_story_details(db, story_id, current_user, request)
    return conditional_model_response(request, response, result)


@router.patch("/{story_id}", response_model=StoryOut, status_code=status.HTTP_200_OK)
def update_existing_story(
    story_id: uuid.UUID, # Correctly a UUID
    data: StoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Updates a story owned by the current user."""
    updated_story = story.update_story(db, story_id, data, current_user)
    story_cache.invalidate_story(str(updated_story.id))
    return StoryOut(
        id=str(updated_story.id),
        title=updated_story.title,
        content=updated_story.content,
        user_id=str(updated_story.user_id),
        created_at=updated_story.created_at,
        updated_at=updated_story.updated_at,
        header=updated_story.header,
        cover_image_url=updated_story.cover_image_url,
        is_published=updated_story.is_published,
        status=updated_story.status,
        source=updated_story.source,
        # user=UserSummary.from_orm(new_story.user),
        tags=[
            TagSummary(id=str(tag.id), name=tag.name) for tag in updated_story.tags
        ],
        
        
        user=UserSummary(
            id=str(updated_story.user.id),
            username=updated_story.user.username
        ),
    )


@router.delete("/{story_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_existing_story(
    story_id: uuid.UUID, # Correctly a UUID
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Deletes a story owned by the current user."""
    story.delete_story(db, story_id, current_user)
    story_cache.invalidate_story(str(story_id))
    return None


# --- AI STORY GENERATION ENDPOINTS ---

@router.post(
    "/generate",
    response_model=StoryOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(llm_generate_rate_limiter)],  # LLM = money
)
def generate_ai_story(
    data: StoryGenerateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(can_create_story),
):
    """Generates a new story using an AI model (non-streaming, one-shot)."""
    new_story = story.generate_story(db, data, current_user)
    return StoryOut(
        id=str(new_story.id),
        user_id=str(new_story.user_id),
        title=new_story.title,
        content=new_story.content,
        created_at=new_story.created_at,
        updated_at=new_story.updated_at,
        header=new_story.header,
        cover_image_url=new_story.cover_image_url,
        is_published=new_story.is_published,
        status=new_story.status,
        source=new_story.source,
        user=UserSummary(id=str(new_story.user.id), username=new_story.user.username),
        tags=[TagSummary.model_validate(tag) for tag in new_story.tags]
    )


def _sse(payload: dict) -> str:
    """Format one Server-Sent Event frame."""
    return f"data: {json.dumps(payload)}\n\n"


@router.post(
    "/generate/stream",
    dependencies=[Depends(llm_generate_rate_limiter)],
)
def generate_ai_story_stream(
    data: StoryGenerateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(can_create_story),
):
    """Streams AI story generation over Server-Sent Events.

    Frames sent to the client:
      {"type":"delta","text":"..."}                 a chunk of story text
      {"type":"done","story_id","status","title"}   generation complete + saved
      {"type":"error","message"}                    something failed

    Streaming both fixes the long-generation timeout wall (data flows
    continuously instead of one 2-minute request) and gives the user live
    feedback. The story is persisted only after the full text arrives, using
    the same finalize/moderation path as the non-streaming route.
    """
    prompt = story.build_generation_prompt(data)

    def event_stream():
        collected: list[str] = []
        try:
            # max_tokens MUST be passed here. Omitting it fell back to the global
            # LLM_MAX_TOKENS (8192 ≈ 6,000 words), so every streamed story ignored
            # the requested length — and this is the path the UI actually uses.
            for chunk in story._llm.generate_stream(
                prompt,
                model=data.model_name,
                temperature=data.temperature,
                max_tokens=story.length_max_tokens(data.length_label),
            ):
                collected.append(chunk)
                yield _sse({"type": "delta", "text": chunk})

            full_text = "".join(collected)
            if not full_text.strip():
                yield _sse({"type": "error", "message": "The model returned an empty story."})
                return

            new_story = story.finalize_generated_story(
                db, data, current_user, story_text=full_text, msg_id="gemini-stream"
            )
            story_cache.invalidate_story(str(new_story.id))
            yield _sse({
                "type": "done",
                "story_id": str(new_story.id),
                "status": new_story.status.value if new_story.status else None,
                "title": new_story.title,
            })
        except Exception:
            # Never leak internals to the client; the DB log handler captures
            # the full traceback server-side.
            logger.exception("stream generation failed")
            db.rollback()
            yield _sse({"type": "error", "message": "Story generation failed. Please try again."})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            # Disable proxy buffering so chunks reach the browser immediately.
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post(
    "/{story_id}/feedback",
    response_model=StoryOut,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(llm_generate_rate_limiter)],  # LLM = money
)
def apply_feedback_to_story(
    story_id: uuid.UUID, # Correctly a UUID
    data: StoryFeedbackIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Regenerates an AI story with new feedback."""
    regenerated_story = story.regenerate_with_feedback(
        db, story_id, data.feedback, current_user, length_label=data.length_label,
    )
    return StoryOut(
        id=str(regenerated_story.id),
        user_id=str(regenerated_story.user_id),
        title=regenerated_story.title,
        content=regenerated_story.content,
        created_at=regenerated_story.created_at,
        updated_at=regenerated_story.updated_at,
        header=regenerated_story.header,
        cover_image_url=regenerated_story.cover_image_url,
        is_published=regenerated_story.is_published,
        source=regenerated_story.source,
        user=UserSummary(id=str(regenerated_story.user.id), username=regenerated_story.user.username),
        tags=[TagSummary.model_validate(tag) for tag in regenerated_story.tags]
    )


@router.post("/{story_id}/publish", response_model=StoryOut, status_code=status.HTTP_200_OK)
def publish_a_story(
    story_id: uuid.UUID, # Correctly a UUID
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Publishes a story, making it visible to all users."""
    published_story = story.publish_story(db, story_id, current_user)
    story_cache.invalidate_story(str(published_story.id))
    return StoryOut(
        id=str(published_story.id),
        title=published_story.title,
        content=published_story.content,
        user_id=str(published_story.user_id),
        created_at=published_story.created_at,
        updated_at=published_story.updated_at,
        header=published_story.header,
        cover_image_url=published_story.cover_image_url,
        is_published=published_story.is_published,
        source=published_story.source,
        # user=UserSummary.from_orm(new_story.user),
        tags=[
            TagSummary(id=str(tag.id), name=tag.name) for tag in published_story.tags
        ],
        
        
        user=UserSummary(
            id=str(published_story.user.id),
            username=published_story.user.username
        ),
    )


@router.post("/{story_id}/unpublish", response_model=StoryOut, status_code=status.HTTP_200_OK)
def unpublish_a_story(
    story_id: uuid.UUID, # Correctly a UUID
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Unpublishes a story, hiding it from public view."""
    unpublished_story = story.unpublish_story(db, story_id, current_user)
    story_cache.invalidate_story(str(unpublished_story.id))
    return StoryOut.model_validate(unpublished_story, from_attributes=True)

