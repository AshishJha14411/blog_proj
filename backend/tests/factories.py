import factory
from factory.alchemy import SQLAlchemyModelFactory
from pytest_factoryboy import register  # <-- ADD THIS IMPORT
from app.models.user import User
from app.models.role import Role
from app.models.stories import Story
from app.models.comment import Comment
from app.models.like import Like
from app.models.bookmarks import Bookmark
from app.models.flag import Flag
from app.dependencies import get_password_hasher
from app.models.password_reset_token import PasswordResetToken
from datetime import datetime, timedelta,timezone
# from .conftest import BaseFactory
from app.utils.security import hash_password
import uuid
class BaseFactory(SQLAlchemyModelFactory):
    class Meta:
        abstract = True
        sqlalchemy_session = None            # injected by tests
        sqlalchemy_session_persistence = "flush"


@register  # <-- ADD THIS
class RoleFactory(BaseFactory):
    class Meta:
        model = Role
    id = factory.LazyFunction(uuid.uuid4)
    name = "user"
    description = None

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        session = cls._meta.sqlalchemy_session
        name = kwargs.get("name", "user")
        existing = session.query(Role).filter_by(name=name).one_or_none()
        if existing:
            return existing
        return super()._create(model_class, *args, **kwargs)


@register
class UserFactory(BaseFactory):
    class Meta:
        model = User
    id = factory.LazyFunction(uuid.uuid4)
    username = factory.Faker("user_name")
    email = factory.Faker("email")
    password_hash = factory.LazyFunction(
        lambda: get_password_hasher().hash("password123")
    )
    # --- END FIX ---
    
    role = factory.SubFactory(RoleFactory)


@register
class PasswordResetTokenFactory(BaseFactory):
    class Meta:
        model = PasswordResetToken

    id = factory.LazyFunction(uuid.uuid4)
    # virtual relation; not a model column
    user = factory.SubFactory(UserFactory)
    token = factory.Faker("bothify", text="????????????????????????????????")
    expires_at = factory.LazyFunction(lambda: datetime.utcnow() + timedelta(hours=1))
    used = False

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        # map the virtual `user` param to the real FK
        user = kwargs.pop("user", None)
        if user is not None:
            kwargs["user_id"] = getattr(user, "id", user)
        return super()._create(model_class, *args, **kwargs)
@register
class StoryFactory(BaseFactory):
    """Factory for creating Story models."""
    class Meta:
        model = Story

    id = factory.LazyFunction(uuid.uuid4)
    title = factory.Faker("sentence", nb_words=4)
    content = factory.Faker("text", max_nb_chars=500)
    is_published = False
    
    # This automatically creates a UserFactory and links it as the author
    user = factory.SubFactory(UserFactory)
    
    
@register
class CommentFactory(BaseFactory):
    """Factory for creating Comment models."""
    class Meta:
        model = Comment

    id = factory.LazyFunction(uuid.uuid4)
    content = factory.Faker("sentence", nb_words=6)
    
    # Link to a user and a story
    user = factory.SubFactory(UserFactory)
    story = factory.SubFactory(StoryFactory)

@register
class LikeFactory(BaseFactory):
    """Factory for creating Like models."""
    class Meta:
        model = Like

    id = factory.LazyFunction(uuid.uuid4)
    
    # Link to a user and a story
    user = factory.SubFactory(UserFactory)
    story = factory.SubFactory(StoryFactory)

@register
class BookmarkFactory(BaseFactory):
    """Factory for creating Bookmark models."""
    class Meta:
        model = Bookmark

    id = factory.LazyFunction(uuid.uuid4)
    
    # Link to a user and a story
    user = factory.SubFactory(UserFactory)
    story = factory.SubFactory(StoryFactory)
@register
class ModeratorFactory(UserFactory):
    role = factory.LazyFunction(lambda: RoleFactory(name="moderator"))

@register
class FlagFactory(BaseFactory):
    class Meta:
        model = Flag

    id = factory.LazyFunction(uuid.uuid4)
    reason = factory.Faker("text", max_nb_chars=100)
    status = "open"

    # optional inputs (not real model columns)
    flagged_by_user = None
    story = None
    comment = None

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """
        Create the Flag instance with valid foreign keys.
        Ensures IDs are set *before* flush to avoid IntegrityError.
        """
        user = kwargs.pop("flagged_by_user", None) or ModeratorFactory()
        story = kwargs.pop("story", None)
        comment = kwargs.pop("comment", None)

        # prepare kwargs for real columns
        kwargs["flagged_by_user_id"] = getattr(user, "id", user)
        kwargs["story_id"] = getattr(story, "id", story)
        kwargs["comment_id"] = getattr(comment, "id", comment)

        # continue with normal SQLAlchemy create
        return super()._create(model_class, *args, **kwargs)
