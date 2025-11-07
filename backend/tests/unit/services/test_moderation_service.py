# tests/unit/services/test_moderation_service.py

import uuid
import pytest
from sqlalchemy.orm import Session
from fastapi import HTTPException

import app.services.moderation as mod_service
from app.models.flag import Flag
from app.models.stories import Story, StoryStatus
from app.models.comment import Comment
from app.models.tags import Tag

from tests.factories import (
    UserFactory,
    RoleFactory,
    StoryFactory,
    CommentFactory,
)

# --- Simple sink to capture notify() without real side effects ---
class NotifySink:
    def __init__(self):
        self.calls = []
    def __call__(self, db, *, recipient_id, actor_id, action, target_type, target_id):
        self.calls.append({
            "recipient_id": recipient_id,
            "actor_id": actor_id,
            "action": action,
            "target_type": target_type,
            "target_id": target_id,
        })


# -------------------------------------------------------------------
# Flagging: stories & comments
# -------------------------------------------------------------------

def test_flag_story_happy_path(db_session: Session):
    reporter = UserFactory(role=RoleFactory(name="user"))
    author = UserFactory(role=RoleFactory(name="creator"))
    story = StoryFactory(user=author)

    flag = mod_service.flag_story(db_session, story.id, "spam", reporter)
    assert isinstance(flag, Flag)
    assert flag.story_id == story.id
    assert flag.flagged_by_user_id == reporter.id
    assert flag.status == "open"

def test_flag_story_404(db_session: Session):
    reporter = UserFactory(role=RoleFactory(name="user"))
    with pytest.raises(HTTPException) as exc:
        mod_service.flag_story(db_session, uuid.uuid4(), "bad", reporter)
    assert exc.value.status_code == 404

def test_flag_comment_happy_path(db_session: Session):
    reporter = UserFactory(role=RoleFactory(name="user"))
    author = UserFactory(role=RoleFactory(name="creator"))
    story = StoryFactory(user=author)
    comment = CommentFactory(user=author, story=story)

    flag = mod_service.flag_comment(db_session, comment.id, "abuse", reporter)
    assert isinstance(flag, Flag)
    assert flag.comment_id == comment.id
    assert flag.flagged_by_user_id == reporter.id
    assert flag.status == "open"

def test_flag_comment_404(db_session: Session):
    reporter = UserFactory(role=RoleFactory(name="user"))
    with pytest.raises(HTTPException) as exc:
        mod_service.flag_comment(db_session, uuid.uuid4(), "bad", reporter)
    assert exc.value.status_code == 404


# -------------------------------------------------------------------
# List / Resolve flags
# -------------------------------------------------------------------

def test_list_open_flags_returns_only_open_sorted_desc(db_session: Session):
    u = UserFactory(role=RoleFactory(name="user"))
    s = StoryFactory(user=UserFactory(role=RoleFactory(name="creator")))

    f1 = mod_service.flag_story(db_session, s.id, "first", u)
    f2 = mod_service.flag_story(db_session, s.id, "second", u)
    # Manually resolve f1 so only f2 remains open
    f1.status = "resolved"; db_session.commit()

    open_flags = mod_service.list_open_flags(db_session)
    assert [f.id for f in open_flags] == [f2.id]  # only latest open one

def test_resolve_flag_happy_path(db_session: Session):
    mod = UserFactory(role=RoleFactory(name="moderator"))
    s = StoryFactory(user=UserFactory(role=RoleFactory(name="creator")))
    fl = mod_service.flag_story(db_session, s.id, "check", mod)

    out = mod_service.resolve_flag(db_session, fl.id, "resolved", mod)
    assert out.status == "resolved"
    assert out.resolved_by == mod.id
    assert out.resolved_at is not None

def test_resolve_flag_invalid_status_400(db_session: Session):
    mod = UserFactory(role=RoleFactory(name="moderator"))
    s = StoryFactory(user=UserFactory(role=RoleFactory(name="creator")))
    fl = mod_service.flag_story(db_session, s.id, "check", mod)

    with pytest.raises(HTTPException) as exc:
        mod_service.resolve_flag(db_session, fl.id, "nope", mod)
    assert exc.value.status_code == 400

def test_resolve_flag_404(db_session: Session):
    mod = UserFactory(role=RoleFactory(name="moderator"))
    with pytest.raises(HTTPException) as exc:
        mod_service.resolve_flag(db_session, uuid.uuid4(), "resolved", mod)
    assert exc.value.status_code == 404


# -------------------------------------------------------------------
# Approve / Reject (and side-effects on flags + notifications)
# -------------------------------------------------------------------

def test_approve_story_updates_fields_closes_flags_and_notifies(db_session: Session, monkeypatch):
    mod = UserFactory(role=RoleFactory(name="moderator"))
    author = UserFactory(role=RoleFactory(name="creator"))
    s = StoryFactory(user=author)
    # seed an open flag
    fl = mod_service.flag_story(db_session, s.id, "sus", mod)

    sink = NotifySink()
    monkeypatch.setattr(mod_service, "notify", sink)

    out = mod_service.approve_story(db_session, s.id, mod, note="looks good")
    assert out.id == s.id
    assert out.status == StoryStatus.published
    assert out.is_published is True
    assert out.is_flagged is False

    # all open flags on this story should be moved to "approved" and annotated
    refreshed_flag = db_session.get(Flag, fl.id)
    assert refreshed_flag.status == "approved"
    assert refreshed_flag.resolved_by_id == mod.id
    assert refreshed_flag.resolved_at is not None
    assert "Moderator Note: looks good" in (refreshed_flag.reason or "")

    # notification emitted to author
    assert len(sink.calls) == 1
    n = sink.calls[0]
    assert n["recipient_id"] == author.id
    assert n["actor_id"] == mod.id
    assert n["action"] == "story_approved"
    assert n["target_type"] == "story"
    assert n["target_id"] == s.id

def test_reject_story_updates_fields_closes_flags_and_notifies(db_session: Session, monkeypatch):
    mod = UserFactory(role=RoleFactory(name="moderator"))
    author = UserFactory(role=RoleFactory(name="creator"))
    s = StoryFactory(user=author)
    fl = mod_service.flag_story(db_session, s.id, "sus", mod)

    sink = NotifySink()
    monkeypatch.setattr(mod_service, "notify", sink)

    out = mod_service.reject_story(db_session, s.id, mod, reason="bad content")
    assert out.id == s.id
    assert out.status == StoryStatus.rejected
    assert out.is_published is False
    assert out.is_flagged is True

    refreshed_flag = db_session.get(Flag, fl.id)
    assert refreshed_flag.status == "rejected"
    assert refreshed_flag.resolved_by_id == mod.id
    assert "bad content" in (refreshed_flag.reason or "")

    assert len(sink.calls) == 1
    n = sink.calls[0]
    assert n["recipient_id"] == author.id
    assert n["actor_id"] == mod.id
    assert n["action"] == "story_rejected"
    assert n["target_id"] == s.id


# -------------------------------------------------------------------
# Moderation queue filters
# -------------------------------------------------------------------

def test_moderation_queue_filters_by_flag_status_author_and_tag(db_session: Session):
    author1 = UserFactory(role=RoleFactory(name="creator"))
    author2 = UserFactory(role=RoleFactory(name="creator"))

    # Create stories with different states
    s_flagged = StoryFactory(user=author1)
    s_flagged.is_flagged = True
    s_flagged.status = StoryStatus.generated
    db_session.commit()

    s_published = StoryFactory(user=author1)
    s_published.is_flagged = False
    s_published.status = StoryStatus.published
    db_session.commit()

    s_rejected = StoryFactory(user=author2)
    s_rejected.is_flagged = True
    s_rejected.status = StoryStatus.rejected
    db_session.commit()

    # Tag one of them
    tag_alpha = Tag(name="alpha")
    db_session.add(tag_alpha); db_session.commit()
    s_flagged.tags.append(tag_alpha); db_session.commit()

    # Default (no status_filter) -> returns is_flagged == True
    total, items = mod_service.moderation_queue(db_session, status_filter=None, author_id=None, tag=None, limit=10, offset=0)
    assert total >= 2
    ids = {i.id for i in items}
    assert s_flagged.id in ids and s_rejected.id in ids

    # Filter by status
    total_gen, items_gen = mod_service.moderation_queue(db_session, status_filter=StoryStatus.generated, author_id=None, tag=None, limit=10, offset=0)
    assert all(i.status == StoryStatus.generated for i in items_gen)

    # Filter by author
    total_a1, items_a1 = mod_service.moderation_queue(db_session, status_filter=None, author_id=author1.id, tag=None, limit=10, offset=0)
    assert all(i.user_id == author1.id for i in items_a1)

    # Filter by tag
    total_t, items_t = mod_service.moderation_queue(db_session, status_filter=None, author_id=None, tag="alpha", limit=10, offset=0)
    assert total_t >= 1
    assert s_flagged.id in {i.id for i in items_t}


# -------------------------------------------------------------------
# Profanity detector wrapper
# -------------------------------------------------------------------

@pytest.mark.parametrize(
    "texts,expected",
    [
        (["clean text", "another clean"], (False, [])),
        (["this is shit", ""], (True, ["profanity"])),
        (["", "ok", "fuck"], (True, ["profanity"])),
    ],
)
def test_moderate_content_detects_profanity(texts, expected):
    flagged, cats = mod_service.moderate_content(texts)
    if expected[0] is False:
        assert flagged is False and cats == []
    else:
        assert flagged is True and "profanity" in cats
