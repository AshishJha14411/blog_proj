from __future__ import annotations
from app.utils.time import utcnow
from datetime import datetime, timedelta
from typing import Iterable, List, Optional, Tuple
import uuid
import base64
import re
from fastapi import HTTPException, status, Request
from sqlalchemy import text, func, or_, and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy.orm.exc import StaleDataError
from sqlalchemy.orm.attributes import set_committed_value
# Import all necessary models
from app.models.like import Like
from app.models.bookmarks import Bookmark
from app.models.comment import Comment
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
from app.authz import Perm, has_perm, authorize_owned
# Initialize the LLM Adapter once
_llm = LLMAdapter()

# WHY: soft-deleted (is_disabled) authors keep their non-flagged stories —
# User.stories has no delete-orphan cascade (see models/user.py) — but the
# byline shouldn't keep advertising a deleted account's real username.
DELETED_USER_LABEL = "Deleted User"


# Presentation-only overrides for LIST responses.
#
# /** WHY set_committed_value AND NOT plain assignment: assigning to a mapped
#     column marks the instance dirty, and the async request path now runs a
#     unit-of-work that COMMITS at the end of every request (dependencies.
#     get_async_db). A display-only tweak would therefore be flushed — a plain
#     GET of the story list would permanently overwrite a disabled author's real
#     username with "Deleted User", and truncating `content` for a card would
#     DESTROY the story body in Postgres. `set_committed_value` writes the
#     attribute as though it had been loaded that way, so it produces no history
#     and nothing to flush. **/
# /** NOTE the previous docstring claimed these mutations were "never committed".
#     That was true under the old read-only sync session and silently stopped
#     being true when the read path became transactional. **/
_EXCERPT_CHARS = 280
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")


def _mask_deleted_authors(items: List[Story]) -> None:
    """Show a placeholder byline for disabled authors, without touching the row."""
    for item in items:
        if item.user is not None and item.user.is_disabled:
            set_committed_value(item.user, "username", DELETED_USER_LABEL)


def _excerpt_for_list(items: List[Story]) -> None:
    """Replace full HTML bodies with a short plain-text excerpt.

    /** WHY: list endpoints were serialising every story's ENTIRE body. Measured
        against production, `GET /stories/?limit=10` returned ~60KB and ~350ms of
        a 1.2s request was pure transfer — for cards that only render three
        clamped lines. **/
    /** BONUS: the card renders `post.content` as TEXT, so raw markup was being
        displayed literally ("<h1>The Sclera of Rain...</h1>"). Stripping tags
        fixes that visible bug at the same time. **/
    /** Detail endpoints are untouched — they still return the full body. **/
    """
    for item in items:
        text = _WHITESPACE_RE.sub(" ", _HTML_TAG_RE.sub(" ", item.content or "")).strip()
        excerpt = text[:_EXCERPT_CHARS] + ("…" if len(text) > _EXCERPT_CHARS else "")
        set_committed_value(item, "content", excerpt)


# --------------------------------------------------------------------------
# Tags
# --------------------------------------------------------------------------
# /** WHY: AI-generated stories were landing with ZERO tags — `create_story`
#     accepted `tag_names` but the generation path never did, so every story
#     written through the generator was untaggable and the tag filter had
#     nothing to filter on (production: 0 rows in `tags`, 0 in `story_tags`).
#     The generator already collects a `genre`, which is exactly the axis a
#     reader browses by, so genre is promoted into a real tag rather than
#     asking the author for the same information twice. **/
_TAG_MAX_LEN = 50
_TAG_SPLIT_RE = re.compile(r"[,/&+|]|\band\b", re.IGNORECASE)
_TAG_STRIP_RE = re.compile(r"[^a-z0-9 -]")


def normalize_tag(raw: str) -> Optional[str]:
    """Clean free text into a usable tag name, or None if nothing is left.

    /** DELIBERATELY NOT a controlled vocabulary. Whatever genre the author
        chose becomes the tag as they wrote it — there is no alias table folding
        "sci-fi" onto a canonical "science-fiction", because that is a curated
        picklist in disguise and it silently overrides the author's words.
        Near-duplicate tags are accepted as the cost of that, and are a
        housekeeping job for later rather than something to pre-empt here. **/

    The transformation is presentational only: lowercase, drop punctuation,
    collapse whitespace, hyphenate. `"  Sci-Fi!! "` becomes `"sci-fi"`, so
    casing and stray punctuation alone don't create separate rows.
    """
    if not raw:
        return None
    name = _TAG_STRIP_RE.sub(" ", str(raw).strip().lower())
    name = _WHITESPACE_RE.sub(" ", name.replace("-", " ")).strip()
    if not name:
        return None
    return name.replace(" ", "-")[:_TAG_MAX_LEN].strip("-") or None


def tags_from_genre(genre: Optional[str], extra: Optional[Iterable[str]] = None) -> List[str]:
    """Convert a story's genre into tag names — the genre *is* the tag.

    A genre is often compound ("Sci-Fi & Horror", "mystery, thriller"), so it
    splits on the usual separators and each part becomes its own tag. `extra`
    (explicit `tag_names` from the client) is merged in and wins on ordering.
    Duplicates are removed while preserving order.
    """
    names: List[str] = []
    for candidate in list(extra or []) + _TAG_SPLIT_RE.split(genre or ""):
        normalized = normalize_tag(candidate)
        if normalized:
            names.append(normalized)
    return list(dict.fromkeys(names))


def resolve_tags(db: Session, names: Iterable[str]) -> List[Tag]:
    """Get-or-create `Tag` rows for `names`, deduped and order-preserving.

    Shared by the authored and generated paths so both clean names identically —
    a tag created by the generator and one typed by an author are the same row.
    """
    tag_objs: List[Tag] = []
    for name in dict.fromkeys(n for n in (normalize_tag(x) for x in names) if n):
        tag = db.query(Tag).filter(Tag.name == name).first()
        if not tag:
            tag = Tag(name=name)
            db.add(tag)
            db.flush()
        tag_objs.append(tag)
    return tag_objs


# /** WHY: AI moderation used to run inline and add LLM latency to every
#     publish. Now the row lands in `pending`, the async task runs the
#     moderator, and the row flips to `published` / `rejected` when it's
#     done. Publish latency drops to a DB insert. **/
# /** WHY-THIS-WAY: enqueue via .delay() — eager-mode in tests, real Redis
#     queue in prod. Under eager mode the transition happens synchronously
#     right after the request commits, so integration tests still see the
#     final state without special-casing. **/
def create_story(db: Session, data: StoryCreate, current_user: User) -> Story:
    if not has_perm(current_user, Perm.STORY_CREATE):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to create a story."
        )
    tag_objs = resolve_tags(db, data.tag_names or [])

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

    if not has_perm(current_user, Perm.STORY_CREATE):
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
    story_text, msg_id = _generate_story_text(
        prompt=full_prompt, model=data.model_name, temperature=data.temperature,
        length_label=data.length_label,
    )
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
    # /** WHY: the genre doubles as the story's tags. Without this, generated
    #     stories carried a genre the reader could see but never browse by, and
    #     the tag index stayed permanently empty. Explicit `tag_names` are
    #     merged in so a future UI can add tags without losing the genre. **/
    new_story.tags = resolve_tags(
        db, tags_from_genre(data.genre, extra=getattr(data, "tag_names", None))
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

# --- READING STORIES (ASYNC) ---
# WHY the read layer is async but the write layer (above/below) is sync — a
# deliberate split, not a half-finished migration:
#   * Reads are the high-fan-out, IO-bound path (list/detail/search dominate
#     traffic). `async def` lets one worker serve many concurrent reads instead
#     of parking a thread per request — the real throughput win. They run on
#     `AsyncSessionLocal` via `get_async_db` (one-txn-per-request UoW).
#   * Writes are low-QPS AND enqueue Celery work that MUST fire only after the
#     row commits (create -> moderate_story_task; update -> re-moderation). The
#     async UoW commits *after* the service returns, so an async write would
#     race the worker against an uncommitted row. Keeping writes on the sync
#     session preserves the correct commit-then-enqueue ordering with no
#     after-commit-hook machinery. Sync and async sessions target the same DB
#     over separate engines and coexist cleanly (FastAPI runs sync routes in a
#     threadpool, async routes on the loop).
async def _populate_interaction_flags(
    db: AsyncSession,
    items: List[Story],
    current_user: Optional[User],
) -> None:
    """ASYNC. Batch-load like/bookmark flags for a page: 2 queries, not 2N."""
    if not current_user or not items:
        for s in items:
            s.is_liked_by_user = False
            s.is_bookmarked_by_user = False
        return

    story_ids = [s.id for s in items]
    liked_res = await db.execute(
        select(Like.story_id).where(
            Like.user_id == current_user.id,
            Like.story_id.in_(story_ids),
        )
    )
    liked = {row[0] for row in liked_res.all()}
    marked_res = await db.execute(
        select(Bookmark.story_id).where(
            Bookmark.user_id == current_user.id,
            Bookmark.story_id.in_(story_ids),
        )
    )
    marked = {row[0] for row in marked_res.all()}
    for s in items:
        s.is_liked_by_user = s.id in liked
        s.is_bookmarked_by_user = s.id in marked


async def search_stories(
    db: AsyncSession, query: str, limit: int, offset: int, current_user: Optional[User]
) -> Tuple[int, List[Story]]:
    """ASYNC. Full-text search over published stories, ranked by relevance.

    Uses the `search_vector` GENERATED tsvector column (title weighted above
    body) with `plainto_tsquery` for the match and `ts_rank` for ordering —
    index-backed by the GIN index, so this scales unlike a LIKE scan. The `:q`
    bind is passed to `execute()` as a params dict (2.0 style).
    """
    # Strip NUL bytes before they reach Postgres: a text column / tsquery can't
    # contain 0x00, and psycopg raises a ValueError (→ 500) if it does. A search
    # box should never 500 on hostile input — drop the bytes and search the rest.
    # (Found by the hypothesis fuzz test, tests/integration/test_fuzz_endpoints.)
    q = (query or "").replace("\x00", "").strip()
    if not q:
        return 0, []

    # `search_vector @@ plainto_tsquery(...)` is the FTS match. Referenced via
    # text() so we don't have to map the generated column onto the ORM.
    match = text("search_vector @@ plainto_tsquery('english', :q)")
    rank = text("ts_rank(search_vector, plainto_tsquery('english', :q)) DESC")

    conditions = (Story.deleted_at.is_(None), Story.is_published.is_(True), match)
    total = (
        await db.execute(select(func.count()).select_from(Story).where(*conditions), {"q": q})
    ).scalar() or 0
    items = (
        await db.execute(
            select(Story)
            .where(*conditions)
            .options(joinedload(Story.user), selectinload(Story.tags))
            .order_by(rank)
            .offset(offset)
            .limit(limit),
            {"q": q},
        )
    ).scalars().unique().all()
    items = list(items)
    await _populate_interaction_flags(db, items, current_user)
    _mask_deleted_authors(items)
    _excerpt_for_list(items)
    return total, items


async def get_all_stories(db: AsyncSession, limit: int, offset: int, tag: Optional[str], author_id: Optional[uuid.UUID], current_user: Optional[User]) -> Tuple[int, List[Story]]:
    """ASYNC. W7: eager-load user + tags so `StoryOut.model_validate(item)`
    doesn't lazy-load per row (async has no implicit lazy IO)."""
    conditions = [Story.deleted_at.is_(None)]
    if not has_perm(current_user, Perm.STORY_MODERATE):
        # /** WHY: `pending` and `rejected` rows must never show up in the
        #     public list, even before the moderation task finishes running.
        #     is_published=True is the strongest single filter. **/
        conditions.append(Story.is_published.is_(True))
    if author_id:
        conditions.append(Story.user_id == author_id)

    def _with_tag(stmt):
        # Tag filter needs a join; applied to both the count and the page.
        return stmt.join(Story.tags).where(Tag.name == tag) if tag else stmt

    total = (
        await db.execute(_with_tag(select(func.count(Story.id)).where(*conditions)))
    ).scalar() or 0
    items = (
        await db.execute(
            _with_tag(
                select(Story)
                .where(*conditions)
                .options(joinedload(Story.user), selectinload(Story.tags))
            )
            .order_by(Story.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
    ).scalars().unique().all()
    items = list(items)
    await _populate_interaction_flags(db, items, current_user)
    _mask_deleted_authors(items)
    _excerpt_for_list(items)
    return total, items


async def get_popular_stories(
    db: AsyncSession, limit: int, days: Optional[int], current_user: Optional[User]
) -> List[Story]:
    """ASYNC. Published stories ranked by reader engagement.

    /** WHY: the home feed was strictly reverse-chronological, so a story that
        readers actually engaged with scrolled away as soon as anything newer
        landed. This surfaces the most-liked / most-discussed work instead. **/

    Score is `likes + comments + bookmarks` computed as three correlated
    subqueries, which keeps this a single round trip and — unlike a JOIN with
    GROUP BY across three one-to-many tables — cannot fan rows out and multiply
    the counts against each other.

    Stories with no engagement at all are excluded rather than padded with
    recent posts: an empty result lets the client hide the section, which is
    honest, where a padded one would quietly relabel "newest" as "popular".
    """
    likes_sq = (
        select(func.count()).select_from(Like)
        .where(Like.story_id == Story.id).scalar_subquery()
    )
    comments_sq = (
        select(func.count()).select_from(Comment)
        .where(Comment.story_id == Story.id).scalar_subquery()
    )
    bookmarks_sq = (
        select(func.count()).select_from(Bookmark)
        .where(Bookmark.story_id == Story.id).scalar_subquery()
    )
    score = likes_sq + comments_sq + bookmarks_sq

    conditions = [Story.deleted_at.is_(None), Story.is_published.is_(True)]
    if days:
        conditions.append(Story.created_at >= datetime.utcnow() - timedelta(days=days))

    rows = (
        await db.execute(
            select(Story, likes_sq, comments_sq, bookmarks_sq)
            .where(*conditions, score > 0)
            .options(joinedload(Story.user), selectinload(Story.tags))
            # created_at breaks ties so the ordering is deterministic across
            # requests — otherwise pagination and caching see rows shuffle.
            .order_by(score.desc(), Story.created_at.desc())
            .limit(limit)
        )
    ).unique().all()

    items: List[Story] = []
    for item, likes, comments, bookmarks in rows:
        # These are plain response-only attributes, not mapped columns, so a
        # direct assignment can't be flushed back to the row (contrast
        # `_excerpt_for_list`, which must use set_committed_value).
        item.likes_count = likes
        item.comments_count = comments
        item.bookmarks_count = bookmarks
        items.append(item)

    await _populate_interaction_flags(db, items, current_user)
    _mask_deleted_authors(items)
    _excerpt_for_list(items)
    return items


def _encode_cursor(created_at: datetime, story_id: uuid.UUID) -> str:
    return base64.urlsafe_b64encode(f"{created_at.isoformat()}|{story_id}".encode()).decode()


def _decode_cursor(cursor: str) -> Tuple[datetime, uuid.UUID]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
        ts_str, id_str = raw.split("|", 1)
        return datetime.fromisoformat(ts_str), uuid.UUID(id_str)
    except Exception:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid cursor.")


async def get_stories_keyset(
    db: AsyncSession, limit: int, cursor: Optional[str], tag: Optional[str],
    author_id: Optional[uuid.UUID], current_user: Optional[User],
) -> Tuple[List[Story], Optional[str]]:
    """ASYNC. Keyset (cursor) pagination — O(1) per page regardless of depth.

    OFFSET makes Postgres scan+discard `offset` rows, so page 10,000 is slow.
    Keyset instead seeks past the last row seen using the ordered key
    `(created_at, id)`: `WHERE (created_at, id) < (cursor)`. The compound key
    (id as tiebreaker) makes the order total, so no row is skipped or repeated
    even when many stories share a created_at.
    """
    conditions = [Story.deleted_at.is_(None)]
    if not has_perm(current_user, Perm.STORY_MODERATE):
        conditions.append(Story.is_published.is_(True))
    if author_id:
        conditions.append(Story.user_id == author_id)
    if cursor:
        c_ts, c_id = _decode_cursor(cursor)
        conditions.append(
            or_(
                Story.created_at < c_ts,
                and_(Story.created_at == c_ts, Story.id < c_id),
            )
        )

    stmt = (
        select(Story)
        .where(*conditions)
        .options(joinedload(Story.user), selectinload(Story.tags))
    )
    if tag:
        stmt = stmt.join(Story.tags).where(Tag.name == tag)
    # Fetch one extra to know whether a next page exists.
    stmt = stmt.order_by(Story.created_at.desc(), Story.id.desc()).limit(limit + 1)

    rows = list((await db.execute(stmt)).scalars().unique().all())
    has_more = len(rows) > limit
    items = rows[:limit]
    next_cursor = _encode_cursor(items[-1].created_at, items[-1].id) if (has_more and items) else None

    await _populate_interaction_flags(db, items, current_user)
    _mask_deleted_authors(items)
    _excerpt_for_list(items)
    return items, next_cursor


async def get_user_stories(db: AsyncSession, user: User, limit: int, offset: int) -> Tuple[int, List[Story]]:
    """ASYNC. All stories authored by `user` (incl. their unpublished drafts)."""
    conditions = (Story.user_id == user.id, Story.deleted_at.is_(None))
    total = (
        await db.execute(select(func.count(Story.id)).where(*conditions))
    ).scalar() or 0
    items = list((
        await db.execute(
            select(Story)
            .where(*conditions)
            .options(joinedload(Story.user), selectinload(Story.tags))
            .order_by(Story.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
    ).scalars().unique().all())
    await _populate_interaction_flags(db, items, user)
    # /stories/me feeds the same PostCard grid, so it gets the same excerpt
    # treatment — otherwise "My Posts" alone kept shipping full story bodies.
    _excerpt_for_list(items)
    return total, items

async def get_story_details(db: AsyncSession, story_id: uuid.UUID, current_user: Optional[User], request: Request) -> StoryOut:
    """ASYNC. Async SQLAlchemy 2.0 style: build a `select()`, `await db.execute`,
    pull rows off the Result. Relationships are eager-loaded (joinedload/
    selectinload) because async has no implicit lazy IO — touching an unloaded
    relationship would raise. No commit here: get_async_db owns the transaction."""
    result = await db.execute(
        select(Story)
        .options(joinedload(Story.user), selectinload(Story.tags))
        .where(Story.id == story_id, Story.deleted_at.is_(None))
    )
    story = result.scalars().first()
    if not story:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Story not found")

    if not story.is_published and not (
        current_user and (story.user_id == current_user.id or has_perm(current_user, Perm.STORY_MODERATE))
    ):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Story not found")

    # Like/bookmark flags — one query each.
    if current_user:
        liked = await db.execute(select(Like.id).where(Like.user_id == current_user.id, Like.story_id == story.id))
        story.is_liked_by_user = liked.first() is not None
        marked = await db.execute(select(Bookmark.id).where(Bookmark.user_id == current_user.id, Bookmark.story_id == story.id))
        story.is_bookmarked_by_user = marked.first() is not None
    else:
        story.is_liked_by_user = False
        story.is_bookmarked_by_user = False

    # Log the view (staged; committed by the request's unit-of-work seam).
    db.add(ViewHistory(
        story_id=story.id, user_id=current_user.id if current_user else None,
        ip_address=request.client.host, user_agent=request.headers.get("user-agent")
    ))

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
        status=story.status,
        genre=story.genre,
        tone=story.tone,
        length_label=story.length_label,
        summary=story.summary,
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
    try:
        db.commit()
    except StaleDataError:
        # Optimistic-lock miss: another write bumped row_version between our
        # read and commit. Tell the client to refetch and retry, don't clobber.
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This story was modified by someone else. Refresh and try again.",
        )
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
def regenerate_with_feedback(
    db: Session, story_id: uuid.UUID, feedback: str, current_user: User,
    length_label: str | None = None,
) -> Story:
    story = db.get(Story, story_id)
    if not story:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Story not found")
    _ensure_authorization(story, current_user)

    # Length precedence: an explicit override from the request wins (the preview
    # page's length control), otherwise carry the story's original length so a
    # revision can't silently turn a `short` piece into a long one.
    _stored = story.length_label.value if getattr(story.length_label, "value", None) else story.length_label
    _len = length_label or _stored
    if length_label and _stored != length_label:
        # Persist the change so subsequent revisions keep the NEW length.
        story.length_label = LengthLabel(length_label)
    regen_prompt = _build_regen_prompt(
        base_prompt=story.prompt or "", feedback=feedback, length_label=_len,
    )
    new_text, msg_id = _generate_story_text(
        prompt=regen_prompt, model=story.model_name, temperature=story.temperature,
        length_label=_len,
    )
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
    # Owner (with STORY_UPDATE_OWN) or a moderator (STORY_MODERATE) may act.
    authorize_owned(user, post, own_perm=Perm.STORY_UPDATE_OWN, any_perm=Perm.STORY_MODERATE)

def _generate_story_text(
    *, prompt: str, model: str, temperature: float, length_label: str | None = None
) -> Tuple[str, str]:
    # Cap output by the requested length. Falls back to the `short` budget rather
    # than the global 8192 when no label is given (regeneration), so an unlabelled
    # request can't quietly become a 6,000-word story.
    text, msg_id = _llm.generate(
        prompt,
        model=model,
        temperature=temperature,
        max_tokens=length_max_tokens(length_label),
        timeout=settings.LLM_TIMEOUT,
    )
    if not text.strip():
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail="LLM returned empty text")
    return text, msg_id

# Concrete word targets per length label.
#
# /** HISTORY: an earlier revision used open-ended "at least N words" framing to
#     stop the model emitting a few lines. It over-corrected — every label,
#     including `flash` and `short`, then had a floor and NO ceiling, so short
#     requests produced 1,000-1,800+ word pieces. **/
# /** WHY-THIS-WAY: a BOUNDED range (floor AND ceiling) plus a per-label token
#     cap. The range stops the model under-writing; the ceiling and the cap stop
#     it over-writing. `max_tokens` is the only *enforceable* limit — prompt text
#     is a request the model may ignore, a token cap is arithmetic. **/
# /** NOTE token budgets are deliberately ~2x the upper word bound (English prose
#     runs ~1.4 tokens/word, plus HTML tag overhead). The cap is a backstop
#     against runaway generation, NOT the target — too tight and stories get
#     truncated mid-sentence, which is worse than being slightly long. **/
# /** TUNING (2026-07-30): flash and short were doubled after the first pass read
#     too short in practice. medium/long were nudged up so the bands stay
#     strictly ordered — otherwise `short` (max 2,200) would have overlapped
#     `medium` (min 1,800) and the labels would stop meaning anything. **/
_LENGTH_SPEC: dict[str, dict] = {
    "flash":  {"min": 600,  "max": 1200, "max_tokens": 2600, "expand": False},
    "short":  {"min": 1400, "max": 2200, "max_tokens": 4600, "expand": False},
    "medium": {"min": 2600, "max": 3600, "max_tokens": 7000, "expand": True},
    "long":   {"min": 4000, "max": 5000, "max_tokens": 8192, "expand": True},
}


def _length_spec(length_label: str | None) -> dict:
    return _LENGTH_SPEC.get((length_label or "short"), _LENGTH_SPEC["short"])


def length_max_tokens(length_label: str | None) -> int:
    """Hard output ceiling for a length label, never above the global setting.

    Both the blocking and the STREAMING generate paths must use this — the
    streaming route previously passed no max_tokens at all, so it silently used
    the global 8192 (~6,000 words) regardless of the requested length.
    """
    return min(_length_spec(length_label)["max_tokens"], settings.LLM_MAX_TOKENS)


def _build_story_prompt(user_prompt: str, genre: str|None, tone: str|None, length_label: str|None) -> str:
    spec = _length_spec(length_label)
    lo, hi = spec["min"], spec["max"]
    length_target = f"a story of approximately {lo:,}–{hi:,} words"

    # /** WHY conditional: "do not stop early / keep writing" was previously
    #     applied to EVERY length, which actively fought the `flash` and `short`
    #     targets — the model was being told to be brief and to keep going in the
    #     same breath, and length instructions lose that fight. Only the long
    #     labels get the expansion push now; the short ones get a stop cue. **/
    if spec["expand"]:
        pacing = (
            f"Do not summarize or write an outline. Develop the middle properly —\n"
            f"expand scenes, dialogue and description until the story genuinely\n"
            f"reaches about {lo:,} words. Do not stop early."
        )
    else:
        pacing = (
            f"Be disciplined about length: this must land between {lo:,} and {hi:,}\n"
            f"words. Stop as soon as the story is complete — do NOT pad it out,\n"
            f"add extra scenes, or continue past roughly {hi:,} words."
        )

    return f"""
You are a skilled fiction writer. Write {length_target}, based on the instructions below.

Write a COMPLETE story — a beginning, a middle, and a real ending.
{pacing}

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

def _build_regen_prompt(base_prompt: str, feedback: str, length_label: str | None = None) -> str:
    spec = _length_spec(length_label)
    return (
        "Revise the following story per the reader feedback.\n\n"
        "Guidelines:\n"
        "- Preserve the core idea and characters.\n"
        "- Improve pacing and clarity.\n"
        # State the range explicitly — "keep the same length range" told the model
        # nothing, since it never sees the original length instruction.
        f"- Keep the length between {spec['min']:,} and {spec['max']:,} words.\n"
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
