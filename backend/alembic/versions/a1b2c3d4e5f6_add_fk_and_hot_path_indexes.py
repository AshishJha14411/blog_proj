"""Add FK and hot-path indexes

Adds indexes that the auto-generated baseline missed:

* likes.user_id, likes.story_id — the like/bookmark lookup by user is on
  every story-list request (see the batched IN-lookup in
  services/story._populate_interaction_flags).
* bookmarks.user_id, bookmarks.story_id — same reason.
* comments.user_id, comments.story_id — /stories/{id}/comments filters by
  story_id and, after the W5 fix, joins Story for the deleted_at guard.
* stories.user_id — /stories/me and admin list_users-per-author.
* stories.is_published — the hot filter on the public list endpoint.
* stories.deleted_at — the soft-delete filter added in W5 hits every
  story query.

All indexes are non-unique and use IF NOT EXISTS so this migration is safe
to re-run against a partially-migrated DB.

Revision ID: a1b2c3d4e5f6
Revises: ea6ae513e2d6
Create Date: 2026-07-21 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "ea6ae513e2d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# name -> (table, columns)
_INDEXES: list[tuple[str, str, list[str]]] = [
    ("ix_likes_user_id",         "likes",     ["user_id"]),
    ("ix_likes_story_id",        "likes",     ["story_id"]),
    ("ix_bookmarks_user_id",     "bookmarks", ["user_id"]),
    ("ix_bookmarks_story_id",    "bookmarks", ["story_id"]),
    ("ix_comments_user_id",      "comments",  ["user_id"]),
    ("ix_comments_story_id",     "comments",  ["story_id"]),
    ("ix_stories_user_id",       "stories",   ["user_id"]),
    ("ix_stories_is_published",  "stories",   ["is_published"]),
    ("ix_stories_deleted_at",    "stories",   ["deleted_at"]),
]


def upgrade() -> None:
    for name, table, columns in _INDEXES:
        op.create_index(name, table, columns, unique=False, if_not_exists=True)


def downgrade() -> None:
    for name, _table, _columns in _INDEXES:
        op.drop_index(name, if_exists=True)
