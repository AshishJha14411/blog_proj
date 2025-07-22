from logging.config import fileConfig
import sys
import os
from sqlalchemy import create_engine, pool
from alembic import context

# ensure project root is on sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# import your Base metadata and settings
from app.core.database import Base
from app.core.config import settings

# import all models so Base.metadata is populated
from app.models.role import Role
from app.models.user import User
from app.models.post import Post
from app.models.tag import Tag, post_tags
from app.models.comment import Comment
from app.models.like import Like
from app.models.view_history import ViewHistory
from app.models.flag import Flag
from app.models.audit_log import AuditLog
from app.models.click import Click
from app.models.otp_verification import OTPVerification
from app.models.password_reset_token import PasswordResetToken
from app.models.analytics_cache import AnalyticsCache
from app.models.ads import Ad
from app.models.bookmarks import Bookmark
from app.models.notification import Notification
from app.models.token_blacklist import TokenBlacklist
# this is the Alembic Config object, which provides
# access to values within the .ini file in use.
config = context.config

# **Override** the URL from alembic.ini with your .env value
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Set up Python logging from the config file
if config.config_file_name:
    fileConfig(config.config_file_name)

# point autogenerate at your models’ metadata
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")  # now a string, not a tuple
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = create_engine(
        settings.DATABASE_URL,  # use the exact same URL
        poolclass=pool.NullPool,
        future=True,
        echo=True,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
