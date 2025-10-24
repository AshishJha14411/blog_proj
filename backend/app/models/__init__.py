# This file turns the 'models' directory into a Python package.
# Its primary job is to import all the SQLAlchemy model classes
# from the other files in this directory so they are registered with Base.
#
# When Alembic (or any other part of the app) runs 'import app.models',
# this file gets executed, which makes SQLAlchemy's Base
# aware of all your tables.

# Core Models
from .role import Role
from .user import User
from .stories import Story
from .story_revision import StoryRevision
from .tags import Tag
from .comment import Comment

# Engagement & Interaction Models
from .like import Like
from .bookmarks import Bookmark
from .flag import Flag
from .click import Click
from .impression import Impression
from .view_history import ViewHistory

# Authentication & Security Models
from .oauth_accounts import OAuthAccount
from .otp_verification import OTPVerification
from .password_reset_token import PasswordResetToken
from .token_blacklist import TokenBlacklist

# System & Logging Models
from .ads import Ads
from .analytics import AnalyticsCache
from .audit_log import AuditLog
from .error_logs import ErrorLog
from .notification import Notification
from .creator_request import CreatorRequest
