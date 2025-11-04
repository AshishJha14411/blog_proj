# tests/unit/services/test_story_service.py
import uuid
from datetime import datetime, timedelta
import pytest

from sqlalchemy.orm import Session

# Services under test
import app.services.story as story_service

from app.models.stories import Story, StoryStatus, ContentSource, FlagSource
from app.models.tags import Tag
from app.models.view_history import ViewHistory
from app.models.flag import Flag
from app.models.like import Like
from app.models.bookmarks import Bookmark
from app.models.story_revision import StoryRevision

from app.schemas.stories import (
    StoryCreate,
    StoryUpdate,
    StoryGenerateIn,
    StoryOut,
)

from tests.factories import (
    UserFactory,
    RoleFactory,
    StoryFactory,
    CommentFactory,  # not directly used but keeps import symmetry
    LikeFactory,
    BookmarkFactory,
)

# -----------------------
# Helpers / stubs
# -----------------------

class _ReqStub:
    """Minimal stand-in for fastapi.Request used by get_story_details."""
    def __init__(self, ip="127.0.0.1", ua="pytest"):
        class _Client:  # mimic request.client.host
            host = ip
        self.client = _Client()
        self.headers = {"user-agent": ua}


def _allow_creator():
    """Ensure we have a 'creator' role available, return a user with it."""
    RoleFactory(name="creator")
    return UserFactory(role=RoleFactory(name="creator"))


def _allow_moderator():
    RoleFactory(name="moderator")
    return UserFactory(role=RoleFactory(name="moderator"))


# -----------------------
# CREATE (human-authored)
# -----------------------

def test_create_story_permission_denied_for_user_role(db_session: Session):
    user = UserFactory(role=RoleFactory(name="user"))
    payload = StoryCreate(title="Nope", content="Body", tag_names=["tag1"], is_published=True)

    with pytest.raises(Exception) as exc:
        story_service.create_story(db_session, payload, user)
    assert "permission" in str(exc.value).lower()


def test_create_story_success_for_creator_role(db_session: Session, monkeypatch):
    creator = _allow_creator()

    # moderation -> clean
    monkeypatch.setattr(story_service, "moderate_content", lambda contents: (False, []))

    payload = StoryCreate(
        title="My Story",
        header="Intro",
        content="<p>Hello world</p>",
        tag_names=["scifi", "drama", "scifi"],  # duplicate to test idempotent tag link
        is_published=True,
    )

    created = story_service.create_story(db_session, payload, creator)
    assert isinstance(created, Story)
    assert created.title == "My Story"
    assert created.is_published is True
    assert created.status == StoryStatus.published
    assert created.source == ContentSource.user

    # Tags: two unique ones created/linked
    names = sorted([t.name for t in created.tags])
    assert names == ["drama", "scifi"]

    # re-run with same tags should not duplicate Tag rows
    before = db_session.query(Tag).count()
    story_service.create_story(db_session, payload, creator)
    after = db_session.query(Tag).count()
    assert after == before  # no new Tag rows created


def test_create_story_flagged_creates_flag_and_unpublishes(db_session: Session, monkeypatch):
    creator = _allow_creator()
    monkeypatch.setattr(story_service, "moderate_content", lambda _: (True, ["profanity"]))

    payload = StoryCreate(
        title="Bad Story",
        content="spoopy content",
        tag_names=["spooky"],
        is_published=True,
    )
    created = story_service.create_story(db_session, payload, creator)
    assert created.is_published is False
    assert created.is_flagged is True
    assert created.flag_source == FlagSource.ai

    # A Flag record should exist for this story
    assert db_session.query(Flag).filter_by(story_id=str(created.id), status="open").count() == 1


# -----------------------
# GENERATE (AI-authored)
# -----------------------

def test_generate_story_success_publishes_when_clean_and_publish_now(db_session: Session, monkeypatch):
    creator = _allow_creator()

    # Fake LLM response
    def fake_gen(prompt, model, temperature, max_tokens, timeout):
        return ("<h1>AI Title</h1><p>AI body</p>", "msg_123")
    monkeypatch.setattr(story_service._llm, "generate", fake_gen)

    monkeypatch.setattr(story_service, "moderate_content", lambda _: (False, []))

    data = StoryGenerateIn(
        title=None,
        summary="ai-summary",
        prompt="Write something about stars",
        genre="scifi",
        tone="optimistic",
        length_label="short",
        publish_now=True,
        temperature=0.5,
        model_name="gpt-4o-mini",
    )

    created = story_service.generate_story(db_session, data, creator)
    assert isinstance(created, Story)
    assert created.is_published is True
    assert created.status == StoryStatus.published
    assert created.provider_message_id == "msg_123"
    assert created.source == ContentSource.ai

    # Revision #1 was created
    revs = db_session.query(StoryRevision).filter_by(stories_id=str(created.id)).all()
    assert len(revs) == 1
    assert revs[0].version == 1
    assert "stars" in (revs[0].prompt or "")


def test_generate_story_flagged_sets_generated_and_flag(db_session: Session, monkeypatch):
    creator = _allow_creator()

    monkeypatch.setattr(
        story_service._llm,
        "generate",
        lambda *a, **k: ("<h1>Bad</h1><p>bad words</p>", "msg_bad"),
    )
    monkeypatch.setattr(story_service, "moderate_content", lambda _: (True, ["toxicity"]))

    data = StoryGenerateIn(prompt="any", publish_now=True)
    created = story_service.generate_story(db_session, data, creator)
    assert created.is_published is False
    assert created.status in (StoryStatus.generated, StoryStatus.draft)
    assert created.is_flagged is True


# -----------------------
# LISTING / FILTERS
# -----------------------

def test_get_all_stories_visibility_and_filters(db_session: Session, monkeypatch):
    user_regular = UserFactory(role=RoleFactory(name="user"))
    mod = _allow_moderator()

    monkeypatch.setattr(story_service, "moderate_content", lambda _: (False, []))

    # Create two tags via story creation
    s1 = story_service.create_story(
        db_session,
        StoryCreate(title="Pub A", content="...", tag_names=["alpha"], is_published=True),
        _allow_creator(),
    )
    s2 = story_service.create_story(
        db_session,
        StoryCreate(title="Draft B", content="...", tag_names=["beta"], is_published=False),
        _allow_creator(),
    )

    # Regular sees only published
    total, items = story_service.get_all_stories(db_session, limit=10, offset=0, tag=None, author_id=None, current_user=user_regular)
    assert total == 1
    assert items[0].id == s1.id

    # Moderator sees both
    total_m, items_m = story_service.get_all_stories(db_session, limit=10, offset=0, tag=None, author_id=None, current_user=mod)
    assert total_m == 2
    ids = {i.id for i in items_m}
    assert {s1.id, s2.id} <= ids

    # Tag filter
    total_alpha, items_alpha = story_service.get_all_stories(db_session, 10, 0, tag="alpha", author_id=None, current_user=mod)
    assert total_alpha == 1
    assert items_alpha[0].id == s1.id

    # Author filter
    total_author, items_author = story_service.get_all_stories(db_session, 10, 0, tag=None, author_id=s2.user_id, current_user=mod)
    assert total_author == 1
    assert items_author[0].id == s2.id


def test_get_user_stories(db_session: Session, monkeypatch):
    author = _allow_creator()
    monkeypatch.setattr(story_service, "moderate_content", lambda _: (False, []))

    story_service.create_story(db_session, StoryCreate(title="t1", content="...", tag_names=[], is_published=True), author)
    story_service.create_story(db_session, StoryCreate(title="t2", content="...", tag_names=[], is_published=False), author)

    total, items = story_service.get_user_stories(db_session, author, limit=10, offset=0)
    assert total == 2
    assert all(s.user_id == author.id for s in items)


# -----------------------
# DETAILS / VIEW LOG / FLAGS
# -----------------------

def test_get_story_details_404_rules_and_flags(db_session: Session, monkeypatch):
    author = _allow_creator()
    other_user = UserFactory(role=RoleFactory(name="user"))
    mod = _allow_moderator()
    monkeypatch.setattr(story_service, "moderate_content", lambda _: (False, []))

    # Create an unpublished story
    s = story_service.create_story(
        db_session,
        StoryCreate(title="hidden", content="...", tag_names=["x"], is_published=False),
        author,
    )

    # Anonymous should 404 (unpublished)
    with pytest.raises(Exception):
        story_service.get_story_details(db_session, s.id, None, _ReqStub())

    # Other regular user should 404
    with pytest.raises(Exception):
        story_service.get_story_details(db_session, s.id, other_user, _ReqStub())

    # Author can view
    out = story_service.get_story_details(db_session, s.id, author, _ReqStub())
    assert isinstance(out, StoryOut)
    assert out.title == "hidden"
    assert out.user.id == author.id

    # Moderator can view
    out2 = story_service.get_story_details(db_session, s.id, mod, _ReqStub())
    assert out2.id == s.id

    # ViewHistory logged
    assert db_session.query(ViewHistory).filter_by(story_id=s.id).count() >= 2

    # Like/Bookmark flags computed
    db_session.add(Like(user_id=author.id, story_id=s.id))
    db_session.add(Bookmark(user_id=author.id, story_id=s.id))
    db_session.commit()
    out3 = story_service.get_story_details(db_session, s.id, author, _ReqStub())
    assert out3.is_liked_by_user is True
    assert out3.is_bookmarked_by_user is True


# -----------------------
# UPDATE / RE-MODERATION
# -----------------------

def test_update_story_by_author_success_and_reflag(db_session: Session, monkeypatch):
    author = _allow_creator()
    monkeypatch.setattr(story_service, "moderate_content", lambda _: (True, ["nsfw"]))

    s = story_service.create_story(
        db_session,
        StoryCreate(title="ok", content="clean", tag_names=["z"], is_published=True),
        author,
    )

    updated = story_service.update_story(
        db_session, s.id, StoryUpdate(title="now bad", content="bad words"), author
    )
    assert updated.is_published is False
    assert updated.is_flagged is True
    assert db_session.query(Flag).filter_by(story_id=s.id).count() >= 1


def test_update_story_permission_denied_for_non_author(db_session: Session, monkeypatch):
    author = _allow_creator()
    other = UserFactory(role=RoleFactory(name="user"))
    monkeypatch.setattr(story_service, "moderate_content", lambda _: (False, []))

    s = story_service.create_story(
        db_session, StoryCreate(title="t", content="c", tag_names=[], is_published=True), author
    )
    with pytest.raises(Exception):
        story_service.update_story(db_session, s.id, StoryUpdate(title="fail"), other)


# -----------------------
# PUBLISH / UNPUBLISH / DELETE
# -----------------------

def test_publish_and_unpublish_story(db_session: Session, monkeypatch):
    author = _allow_creator()
    monkeypatch.setattr(story_service, "moderate_content", lambda _: (False, []))

    s = story_service.create_story(
        db_session, StoryCreate(title="t", content="c", tag_names=[], is_published=False), author
    )

    # Try publish while clean
    s_pub = story_service.publish_story(db_session, s.id, author)
    assert s_pub.is_published is True
    assert s_pub.status == StoryStatus.published

    # Unpublish
    s_unpub = story_service.unpublish_story(db_session, s.id, author)
    assert s_unpub.is_published is False
    assert s_unpub.status == StoryStatus.generated

    # Make it flagged, then publishing should fail
    s_unpub.is_flagged = True
    db_session.commit()
    with pytest.raises(Exception):
        story_service.publish_story(db_session, s.id, author)


def test_delete_story_soft_delete(db_session: Session, monkeypatch):
    author = _allow_creator()
    monkeypatch.setattr(story_service, "moderate_content", lambda _: (False, []))

    s = story_service.create_story(
        db_session, StoryCreate(title="t", content="c", tag_names=[], is_published=True), author
    )

    res = story_service.delete_story(db_session, s.id, author)
    assert "deleted" in res["message"].lower()

    # Soft-deleted means not returned by default listing
    total, items = story_service.get_all_stories(db_session, 10, 0, None, None, author)
    assert all(i.id != s.id for i in items)


# -----------------------
# REGENERATE WITH FEEDBACK
# -----------------------

def test_regenerate_with_feedback_updates_and_adds_revision(db_session: Session, monkeypatch):
    author = _allow_creator()

    monkeypatch.setattr(story_service, "moderate_content", lambda _: (False, []))
    # seed a generated story
    s = story_service.generate_story(
        db_session,
        StoryGenerateIn(prompt="seed", publish_now=False, title="seed title"),
        author,
    )

    # Next generation returns new body
    monkeypatch.setattr(
        story_service._llm,
        "generate",
        lambda *a, **k: ("<p>revised content</p>", "msg_revised"),
    )

    out = story_service.regenerate_with_feedback(db_session, s.id, "more action", author)
    assert out.version == 2
    assert out.is_published is False
    assert out.status == StoryStatus.generated
    assert "revised" in out.content

    revs = db_session.query(StoryRevision).filter_by(stories_id=s.id).order_by(StoryRevision.version).all()
    assert [r.version for r in revs] == [1, 2]
    assert revs[-1].feedback == "more action"
