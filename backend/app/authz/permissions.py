"""Permission catalog and role -> permission mapping.

Design notes:
- A `Perm` is a fine-grained capability (`story:moderate`), not a role. Routes
  and services ask "does this user have Perm.X?" — never "is this user a
  moderator?". That indirection is the whole point: capabilities can be
  re-assigned to roles in ONE place without touching call sites.
- `:own` capabilities (STORY_UPDATE_OWN) are checked together with ownership in
  `policy.authorize_owned`; a separate `_MODERATE` capability grants the
  any-resource variant.
- Roles are hierarchical by construction (each set is built from the one below
  it), so "moderator can do everything a creator can" is expressed once.
"""
from __future__ import annotations

from enum import Enum


class Perm(str, Enum):
    # --- Stories ---
    STORY_CREATE = "story:create"
    STORY_UPDATE_OWN = "story:update:own"
    STORY_DELETE_OWN = "story:delete:own"
    STORY_MODERATE = "story:moderate"        # update / delete / read ANY story
    # --- Comments ---
    COMMENT_CREATE = "comment:create"
    COMMENT_DELETE_OWN = "comment:delete:own"
    COMMENT_MODERATE = "comment:moderate"    # delete ANY comment
    # --- Tags ---
    TAG_CREATE = "tag:create"
    TAG_MANAGE = "tag:manage"                # update / delete tags
    # --- Moderation ---
    MOD_QUEUE = "mod:queue"                  # view the moderation queue
    MOD_RESOLVE = "mod:resolve"              # approve / reject flagged content
    ANALYTICS_VIEW = "analytics:view"
    # --- Admin ---
    ADMIN_USERS = "admin:users"              # list / disable / change roles
    ADMIN_ADS = "admin:ads"
    # --- Creator flow ---
    CREATOR_REQUEST = "creator:request"      # ask to become a creator (users only)


# Built bottom-up so higher roles inherit everything below them.
_USER: set[Perm] = {
    Perm.COMMENT_CREATE,
    Perm.COMMENT_DELETE_OWN,
    Perm.CREATOR_REQUEST,
}

_CREATOR: set[Perm] = (_USER - {Perm.CREATOR_REQUEST}) | {
    # A creator no longer "requests" creator access — they have it.
    Perm.STORY_CREATE,
    Perm.STORY_UPDATE_OWN,
    Perm.STORY_DELETE_OWN,
    Perm.TAG_CREATE,
}

_MODERATOR: set[Perm] = _CREATOR | {
    Perm.STORY_MODERATE,
    Perm.COMMENT_MODERATE,
    Perm.MOD_QUEUE,
    Perm.MOD_RESOLVE,
    Perm.ANALYTICS_VIEW,
}

_SUPERADMIN: set[Perm] = _MODERATOR | {
    Perm.ADMIN_USERS,
    Perm.ADMIN_ADS,
    Perm.TAG_MANAGE,
}

ROLE_PERMS: dict[str, set[Perm]] = {
    "user": _USER,
    "creator": _CREATOR,
    "moderator": _MODERATOR,
    "superadmin": _SUPERADMIN,
}


def role_permissions(role_name: str | None) -> set[Perm]:
    """Permissions for a role name; unknown/None roles get nothing."""
    return ROLE_PERMS.get((role_name or "").lower(), set())
