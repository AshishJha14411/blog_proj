"""
/** WHY: the AI-moderation-to-Celery migration moved the "flag or publish"
    decision out of the request path into an async task. These tests are the
    contract for that task: it must transition state correctly, create a
    Flag on rejection, notify the author, and be safe to redeliver. **/
"""
from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models.flag import Flag
from app.models.stories import FlagSource, Story, StoryStatus
from app.tasks import moderation as moderation_task
from tests.factories import RoleFactory, StoryFactory, UserFactory


def _pending_story(db_session: Session) -> Story:
    """
    /** WHY: the task only acts on rows in the `pending` state; seeded rows
        default to something else. **/
    """
    story = StoryFactory(status=StoryStatus.pending, is_published=False)
    db_session.commit()
    return story


def _patch_task_db_session(monkeypatch, db_session: Session):
    """
    /** WHY: the task opens its own SessionLocal() to survive request context.
        In tests we want the task to see the same rows the test session sees
        (SAVEPOINT-scoped), so we make SessionLocal return the test session. **/
    /** WHY-THIS-WAY: wrapping in a context-managed proxy would be pure. But
        the task only calls `db.close()` on exit — the test session's own
        teardown handles the real cleanup. **/
    """
    class _SessionProxy:
        def __init__(self, real):
            self._real = real

        def __getattr__(self, name):
            return getattr(self._real, name)

        def close(self):
            # Do not close the test session — the outer fixture owns it.
            pass

    monkeypatch.setattr(moderation_task, "SessionLocal", lambda: _SessionProxy(db_session))


def test_task_approves_clean_story(db_session: Session, monkeypatch):
    """A story with no policy hits must transition to published."""
    RoleFactory(name="user")  # for the automod user's role fallback
    story = _pending_story(db_session)
    _patch_task_db_session(monkeypatch, db_session)

    monkeypatch.setattr(moderation_task, "moderate_content", lambda _: (False, []))

    result = moderation_task.moderate_story_task.apply(
        kwargs={"story_id": str(story.id)},
    )
    assert result.successful()
    assert result.result["status"] == "approved"

    db_session.refresh(story)
    assert story.status == StoryStatus.published
    assert story.is_published is True
    assert story.is_flagged is False
    assert db_session.query(Flag).filter_by(story_id=story.id).count() == 0


def test_task_holds_flagged_story_for_review_and_creates_flag(db_session: Session, monkeypatch):
    """A flagged story is HELD for a human, never auto-rejected.

    REGRESSION: this task used to set `rejected` on any keyword hit. Because
    the scan is per-word, the chance of a hit rises with length, so the longer
    the story the more likely it was destroyed — a 4,400-word story was
    auto-rejected on one word while a 78-word one passed. That is a length
    filter disguised as a safety filter.

    The safety property that must NOT regress is the other half: flagged
    content is still never auto-published. It is unlisted, flagged, queued for
    a moderator. Only a human sets `rejected`.
    """
    RoleFactory(name="user")
    story = _pending_story(db_session)
    _patch_task_db_session(monkeypatch, db_session)

    monkeypatch.setattr(
        moderation_task, "moderate_content", lambda _: (True, ["profanity"]),
    )

    result = moderation_task.moderate_story_task.apply(
        kwargs={"story_id": str(story.id)},
    )
    assert result.successful()
    assert result.result["status"] == "flagged"

    db_session.refresh(story)
    assert story.status == StoryStatus.pending, "held for review, not rejected"
    assert story.status != StoryStatus.rejected, "automation must never reject"
    assert story.is_published is False, "flagged content must not go live"
    assert story.is_flagged is True
    assert story.flag_source == FlagSource.ai

    flags = db_session.query(Flag).filter_by(story_id=story.id).all()
    assert len(flags) == 1
    assert flags[0].status == "open"
    assert "profanity" in flags[0].reason


def test_task_is_idempotent(db_session: Session, monkeypatch):
    """A redelivered task with the same story_id must not re-run moderation."""
    RoleFactory(name="user")
    story = _pending_story(db_session)
    _patch_task_db_session(monkeypatch, db_session)

    calls = {"n": 0}
    def spy(_):
        calls["n"] += 1
        return (False, [])
    monkeypatch.setattr(moderation_task, "moderate_content", spy)

    moderation_task.moderate_story_task.apply(kwargs={"story_id": str(story.id)})
    result2 = moderation_task.moderate_story_task.apply(kwargs={"story_id": str(story.id)})

    assert result2.successful()
    assert result2.result["status"] == "duplicate"
    assert calls["n"] == 1  # never re-invoked


def test_task_gracefully_handles_deleted_story(db_session: Session, monkeypatch):
    """If the story was deleted between enqueue and pickup, the task must
    return cleanly without touching moderation or the DB state."""
    RoleFactory(name="user")
    story = _pending_story(db_session)
    story.deleted_at = story.created_at  # soft-delete
    db_session.commit()

    _patch_task_db_session(monkeypatch, db_session)

    called = {"n": 0}
    monkeypatch.setattr(moderation_task, "moderate_content", lambda _: (called.__setitem__("n", called["n"] + 1), (False, []))[1])

    result = moderation_task.moderate_story_task.apply(kwargs={"story_id": str(story.id)})
    assert result.successful()
    assert result.result["status"] == "gone"
    assert called["n"] == 0


def test_task_respects_moderator_decision(db_session: Session, monkeypatch):
    """If a moderator manually resolved the story before the task ran, the
    task must not clobber the moderator's status."""
    RoleFactory(name="user")
    story = StoryFactory(status=StoryStatus.published, is_published=True)
    db_session.commit()
    _patch_task_db_session(monkeypatch, db_session)

    monkeypatch.setattr(moderation_task, "moderate_content", lambda _: (True, ["profanity"]))

    result = moderation_task.moderate_story_task.apply(kwargs={"story_id": str(story.id)})
    assert result.successful()
    assert result.result["status"] == "not_pending"
    db_session.refresh(story)
    # Moderator's choice preserved.
    assert story.status == StoryStatus.published


def test_task_rejects_invalid_story_id_without_retry(db_session: Session):
    """A poisoned queue message (bad UUID) must fail fast, not spin retries."""
    result = moderation_task.moderate_story_task.apply(
        kwargs={"story_id": "not-a-uuid"},
    )
    assert result.successful()
    assert result.result["status"] == "invalid_id"
