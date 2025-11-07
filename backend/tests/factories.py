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
from app.models.tags import Tag
from app.models.ads import Ads
from app.models.click import Click,ClickableType
from app.models.impression import Impression
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
    is_flagged = False
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

@register
class AdFactory(BaseFactory):
    """Factory for creating Ad models with all required fields."""
    class Meta:
        model = Ads

    id = factory.LazyFunction(uuid.uuid4)
    advertiser_name = factory.Faker("company")
    
    # --- FIX: Provide defaults for NOT NULL columns ---
    destination_url = factory.Faker("url") 
    ad_content = factory.Faker("catch_phrase")
    image_url = factory.Faker("image_url")
    weight = 1
    active = True

@register
class ImpressionFactory(BaseFactory):
    """
    FIXED: Uses the _create method to map 'ad' and 'user'
    objects to their real '_id' columns.
    """
    class Meta:
        model = Impression

    id = factory.LazyFunction(uuid.uuid4)
    slot = "sidebar" # Add a default for the NOT NULL field

    # These are "transient" (helper) inputs
    ad = None
    user = None
    story = None
    
    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        # Pop the helper objects
        ad = kwargs.pop("ad", None) or AdFactory()
        user = kwargs.pop("user", None)
        story = kwargs.pop("story", None)
        
        # Set the *real* column kwargs
        kwargs["ad_id"] = getattr(ad, "id", ad)
        if user:
            kwargs["user_id"] = getattr(user, "id", user)
        if story:
            kwargs["story_id"] = getattr(story, "id", story)

        return super()._create(model_class, *args, **kwargs)

@register
class ClickFactory(BaseFactory):
    """
    FIXED: Uses the _create method to handle the
    polymorphic 'clickable' relationship.
    """
    class Meta:
        model = Click
    
    id = factory.LazyFunction(uuid.uuid4)
    ip_address = factory.Faker("ipv4")
    user_agent = factory.Faker("user_agent")
    
    # Define transient (helper) inputs
    clickable = None
    user = None

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        clickable = kwargs.pop("clickable", None)
        user = kwargs.pop("user", None)
        
        # Set the polymorphic fields based on the object type
        if isinstance(clickable, Story):
            kwargs["clickable_type"] = ClickableType.POST
            kwargs["clickable_id"] = clickable.id
        elif isinstance(clickable, Ads):
            kwargs["clickable_type"] = ClickableType.AD
            kwargs["clickable_id"] = clickable.id
        else:
            # Default to creating an Ad if no clickable is specified
            if "clickable_id" not in kwargs:
                default_ad = AdFactory()
                kwargs["clickable_type"] = ClickableType.AD
                kwargs["clickable_id"] = default_ad.id

        if user:
            kwargs["user_id"] = getattr(user, "id", user)

        return super()._create(model_class, *args, **kwargs)
    


@register
class TagFactory(BaseFactory):
    class Meta:
        model = Tag

    id = factory.LazyFunction(uuid.uuid4)
    name = factory.Sequence(lambda n: f"tag_{n}")
    description = None

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """
        Ensure Tag(name) uniqueness across tests. If a Tag with the same
        name exists in the current session, return it instead of creating
        a duplicate.
        """
        session = cls._meta.sqlalchemy_session
        name = kwargs.get("name")
        if name:
            existing = session.query(Tag).filter_by(name=name).one_or_none()
            if existing:
                return existing
        return super()._create(model_class, *args, **kwargs)
