"""
/** WHY: AI moderation used to run inline in the /stories POST handler. That
    added LLM latency to every publish (~200ms on a good day, seconds on a
    bad one), coupled the request thread to a third-party service, and made
    the publish endpoint fail whenever the moderator returned an error. **/

/** WHAT: `moderate_story_task(story_id)` runs `moderate_content` against
    the title + body, then flips the row from `pending` → `published` or
    `rejected` (creating a Flag if flagged), and notifies the author. **/

/** WHY-THIS-WAY:
    - Task takes the story id, not the object — Celery must serialize args
      through JSON, and ORM objects don't survive that trip.
    - Task opens its OWN DB session (SessionLocal()). Request-scoped
      dependencies don't exist in the worker.
    - Idempotency key ties to the story id so a redelivered task doesn't
      double-notify the author. **/
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from celery.exceptions import SoftTimeLimitExceeded

from app.core.database import SessionLocal
from app.models.flag import Flag
from app.models.stories import FlagSource, Story, StoryStatus
from app.services.moderation import moderate_content
from app.services.notifications import notify
from app.services.system import get_automod_user
from app.utils.idempotency import claim_once, release
from app.worker import celery_app

logger = logging.getLogger(__name__)


# recommended by claude opus 4.7:
#   - Retry only on transient / unclear errors. Content decisions themselves
#     should never be retried — the model returned an answer, act on it.
#   - Max retries lower than the email task (2 vs 3): a stuck moderator is
#     less recoverable and blocks story publication for the user.
@celery_app.task(
    name="app.tasks.moderation.moderate_story_task",
    bind=True,
    max_retries=2,
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=5,
    retry_backoff_max=60,
    retry_jitter=True,
)
def moderate_story_task(self, *, story_id: str) -> dict:
    """
    /** WHY: the "was this story pending? yes → decide" work now belongs
        outside the request path. **/
    /** WHAT: loads the story, runs moderation, transitions state, records
        a Flag on rejection, notifies the author. Returns a small dict so
        the result backend has something inspectable. **/
    /** WHY-THIS-WAY: claim_once BEFORE the ORM work so the redelivered
        duplicate short-circuits. If moderation itself raises, we release
        so the retry curve can run again — same check-in / check-out
        pattern as the email task. **/
    """
    dedupe_key = f"moderate:{story_id}"
    if not claim_once(dedupe_key):
        logger.info("moderation skipped, already ran (story_id=%s)", story_id)
        return {"status": "duplicate", "story_id": story_id}

    db = SessionLocal()
    try:
        try:
            story_uuid = uuid.UUID(story_id)
        except ValueError:
            # Bad input from a poisoned queue message — don't retry.
            logger.error("moderate_story_task: invalid story_id=%r", story_id)
            return {"status": "invalid_id", "story_id": story_id}

        story = db.get(Story, story_uuid)
        if story is None or story.deleted_at is not None:
            # Story was deleted between enqueue and task pickup — nothing to do.
            return {"status": "gone", "story_id": story_id}

        if story.status != StoryStatus.pending:
            # Someone (a moderator, most likely) already moved this off pending.
            # Respect their decision — don't clobber their state.
            return {"status": "not_pending", "story_id": story_id, "current": story.status.value}

        flagged, categories = moderate_content([story.title or "", story.content or ""])

        if flagged:
            story.is_flagged = True
            story.flag_source = FlagSource.ai
            story.is_published = False
            story.status = StoryStatus.rejected

            automod = get_automod_user(db)
            db.add(Flag(
                flagged_by_user_id=automod.id,
                story_id=story.id,
                reason="; ".join(categories) or "Flagged by AI moderation",
                status="open",
            ))

            if story.user_id:
                notify(
                    db,
                    recipient_id=story.user_id,
                    action="story_rejected",
                    actor_id=automod.id,
                    target_type="story",
                    target_id=story.id,
                )
        else:
            story.is_flagged = False
            story.flag_source = FlagSource.none
            story.is_published = True
            story.status = StoryStatus.published

            if story.user_id:
                notify(
                    db,
                    recipient_id=story.user_id,
                    action="story_approved",
                    actor_id=None,
                    target_type="story",
                    target_id=story.id,
                )

        story.updated_at = datetime.now(timezone.utc)
        db.commit()

        # Fire the outbound webhook event AFTER the commit — subscribers should
        # only hear about state that's actually durable. Import lazily to keep
        # the webhook/Celery graph out of this module's import path.
        from app.services.webhooks import dispatch_event
        event = "story.rejected" if flagged else "story.published"
        dispatch_event(db, event, {
            "id": str(story.id),
            "title": story.title,
            "user_id": str(story.user_id) if story.user_id else None,
            "status": story.status.value,
        })

        # Invalidate any cached list pages that would still show the pending
        # state. Import here to avoid pulling Redis into moderation's import
        # graph at module load.
        from app.utils import cache as story_cache
        story_cache.invalidate_story(str(story.id))

        return {"status": "flagged" if flagged else "approved", "story_id": story_id}
    except SoftTimeLimitExceeded:
        release(dedupe_key)
        db.rollback()
        raise
    except Exception:
        # Anything unexpected: release the claim so the retry can run.
        release(dedupe_key)
        db.rollback()
        raise
    finally:
        db.close()
