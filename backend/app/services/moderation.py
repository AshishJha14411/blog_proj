import re
from sqlalchemy.orm import Session
from app.utils.time import utcnow
from fastapi import HTTPException, status
from datetime import datetime
from typing import List, Tuple, Optional
import uuid
from app.models.tags import Tag
from app.models.flag import Flag
from app.models.stories import Story, StoryStatus
from app.models.comment import Comment
from app.models.user import User
from app.services.notifications import notify
from app.core.config import settings
from better_profanity import profanity

# /** WHY a whitelist: better_profanity's default list flags "hell", "damn",
#     "ass" and "bastard" — ordinary words in fiction. Any story of a few
#     thousand words will almost certainly contain one, so LONG stories were
#     being auto-REJECTED essentially every time (verified: all four flag True
#     against the default list). On a creative-writing platform that is a
#     product bug, not safety. **/
# /** WHAT: mild/period/exclamatory words that legitimately appear in prose are
#     whitelisted. Slurs and explicit sexual content stay flagged — the point is
#     to stop false positives, not to disable moderation. **/
# /** WHY-THIS-WAY: `load_censor_words(whitelist_words=...)` rebuilds the
#     matcher once at import, so the hot path (`contains_profanity`) is
#     unchanged and stays O(text). **/
_FICTION_WHITELIST = [
    "hell", "hells", "damn", "damned", "damnit", "dammit", "goddamn", "goddamned",
    "ass", "arse", "asses", "bastard", "bastards", "bloody", "bugger", "crap",
    "crappy", "piss", "pissed", "git", "sucks", "screw", "screwed", "screwing",
    "god", "jesus", "christ", "hecks", "heck", "darn", "bollocks", "blimey",
]
profanity.load_censor_words(whitelist_words=_FICTION_WHITELIST)


# --- Flagging Logic ---

def flag_story(db: Session, story_id: uuid.UUID, reason: str, current_user: User) -> Flag:
    story = db.get(Story, story_id)
    if not story:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Story not found")
    
    flag = Flag(
        flagged_by_user_id=current_user.id,
        story_id=story_id,
        reason=reason.strip(),
        status="open"
    )
    db.add(flag)
    db.commit()
    db.refresh(flag)
    return flag

def flag_comment(db: Session, comment_id: uuid.UUID, reason: str, current_user: User) -> Flag:
    comment = db.get(Comment, comment_id)
    if not comment:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Comment not found")
        
    flag = Flag(
        flagged_by_user_id=current_user.id,
        comment_id=comment_id,
        reason=reason.strip(),
        status="open"
    )
    db.add(flag)
    db.commit()
    db.refresh(flag)
    return flag

def list_open_flags(db: Session) -> List[Flag]:
    return db.query(Flag).filter(Flag.status == "open").order_by(Flag.created_at.desc()).all()

# app/services/moderation.py
from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from app.models.flag import Flag
from app.models.user import User
from app.models.audit_log import AuditLog

VALID_FLAG_STATUSES = {"open", "resolved", "ignored"}

def resolve_flag(db: Session, flag_id: UUID, new_status: str, actor: User) -> Flag:
    """
    Update a flag's status with audit fields.
    - Valid statuses: open | resolved | ignored
    - When resolved/ignored -> set resolved_by and resolved_at
    - When open -> clear resolved_* fields
    """
    new_status = (new_status or "").lower()
    if new_status not in VALID_FLAG_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status. Must be one of: open, resolved, ignored."
        )

    flag = db.get(Flag, flag_id)
    if not flag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flag not found")

    before = {"status": flag.status}

    flag.status = new_status
    now = utcnow()

    if new_status in {"resolved", "ignored"}:
        # NOTE: model column is `resolved_by` (UUID), not `resolved_by_id`
        flag.resolved_by = actor.id
        flag.resolved_at = now
    else:  # "open"
        flag.resolved_by = None
        flag.resolved_at = None

    db.commit()
    db.refresh(flag)

    db.add(AuditLog(
        actor_user_id=actor.id,
        action="resolve_flag",
        target_type="flag",
        target_id=str(flag.id),
        after_state={"status": flag.status},
        timestamp=now,
        before_state={"before_state": before}
    ))
    db.commit()

    return flag


def approve_story(db: Session, story_id: uuid.UUID, moderator: User, note: str = "") -> Story:
    story = db.get(Story, story_id)
    if not story:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Story not found")

    story.status = StoryStatus.published
    story.is_published = True
    story.is_flagged = False
    _close_open_flags(db, story_id, moderator.id, "approved", note)
    db.commit()
    db.refresh(story)
    notify(db, recipient_id=story.user_id, actor_id=moderator.id, action="story_approved", target_type="story", target_id=story.id)
    return story

def reject_story(db: Session, story_id: uuid.UUID, moderator: User, reason: str) -> Story:
    story = db.get(Story, story_id)
    if not story:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Story not found")

    story.status = StoryStatus.rejected
    story.is_published = False
    story.is_flagged = True
    _close_open_flags(db, story_id, moderator.id, "rejected", reason)
    db.commit()
    db.refresh(story)
    notify(db, recipient_id=story.user_id, actor_id=moderator.id, action="story_rejected", target_type="story", target_id=story.id)
    return story

def _close_open_flags(db: Session, story_id: uuid.UUID, resolver_id: uuid.UUID, decision: str, note: str):
    flags = db.query(Flag).filter(Flag.story_id == story_id, Flag.status == "open").all()
    for f in flags:
        f.status = decision
        f.resolved_by_id = resolver_id
        f.resolved_at = utcnow()
        if note:
            f.reason = f"{f.reason or ''} | Moderator Note: {note}"

def moderation_queue(
    db: Session,
    status_filter: Optional[StoryStatus],
    author_id: Optional[uuid.UUID],
    tag: Optional[str],
    limit: int,
    offset: int,
    flagged_only: bool = False,
) -> Tuple[int, List[Story]]:
    """/** WHY `flagged_only` is a query filter and not a post-filter on the
        page: the route used to fetch a page, then drop non-flagged rows from
        it in Python. Two things broke. `total` was counted BEFORE the drop, so
        the header ("N items matching this filter") disagreed with the list;
        and a page of 10 could arrive with 9 removed, so pagination showed
        near-empty pages while claiming more existed. Filtering in SQL makes
        the count and the page describe the same set. **/"""
    q = db.query(Story).filter(Story.deleted_at.is_(None))

    if status_filter is not None:
        # ✅ compare with Enum; works for SQLAlchemy Enum columns
        q = q.filter(Story.status == status_filter)

    if flagged_only:
        q = q.filter(Story.is_flagged.is_(True))

    if author_id:
        q =  q.filter(Story.user_id == author_id)

    if tag:
        q = q.join(Story.tags).filter(Tag.name == tag)

    total = q.count()
    items = q.order_by(Story.created_at.desc()).limit(limit).offset(offset).all()
    return total, items

_WORD_RE = re.compile(r"[a-zA-Z']+")


def count_profane_words(texts: List[str]) -> int:
    """Count profane word occurrences across `texts`.

    /** WHY COUNT AND NOT `contains_profanity`: the boolean answers "is there a
        rude word anywhere", which on a creative-writing platform is nearly
        always yes for anything long enough. Counting lets the decision scale
        with how much profanity is actually present rather than whether any
        exists at all. **/

    Occurrences, not distinct words — one word used twenty times is a stronger
    signal than twenty words used once.
    """
    total = 0
    for text in texts:
        for word in _WORD_RE.findall(text or ""):
            if profanity.contains_profanity(word):
                total += 1
    return total


def moderate_content(texts: List[str]) -> Tuple[bool, List[str]]:
    """Scan text for profanity. Returns `(is_flagged, categories)`.

    /** WHY A THRESHOLD: flagging on a single hit made length the real filter.
        Profanity is counted per word, so the chance of at least one hit grows
        with the word count — a 4,400-word horror story tripped it on one word
        while a 78-word one passed. Requiring
        `MODERATION_PROFANITY_THRESHOLD` (default 10) occurrences means the
        signal is "this text is saturated with profanity", which does not
        scale with length in the same way, and lets fiction swear the way
        fiction does.

        Paired with the task change (flagged content is HELD for review, never
        auto-rejected) the failure mode is now: a moderator sees it. **/

    /** ⚠ ACCEPTED RISK: a single slur in an otherwise clean story no longer
        trips this. The threshold is a false-positive fix, not a safety
        upgrade. If a zero-tolerance list is ever needed, add a separate
        severe-terms check that flags at count >= 1, and keep this threshold
        for ordinary profanity — do NOT just lower the threshold, which
        reintroduces the length bias. **/
    """
    threshold = max(1, int(getattr(settings, "MODERATION_PROFANITY_THRESHOLD", 10)))
    hits = count_profane_words(texts)
    if hits >= threshold:
        return True, [f"profanity ({hits} occurrences, threshold {threshold})"]
    return False, []
