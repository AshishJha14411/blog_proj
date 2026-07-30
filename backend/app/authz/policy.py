"""Policy layer: the three ways code asks an authorization question.

- `has_perm(user, perm)` — a plain boolean, for service-level branching.
- `require(perm)` — a FastAPI dependency that 403s if the user lacks `perm`;
  use it in a route's `dependencies=[...]` or as a `current_user` provider.
- `authorize_owned(user, resource, own_perm, any_perm)` — the ownership check:
  allow if the user owns the resource and has `own_perm`, OR has `any_perm`
  (the moderator/admin override). Raises 403/404 otherwise.
"""
from __future__ import annotations

from typing import Any, Callable

from fastapi import Depends, HTTPException, status

from app.authz.permissions import Perm, role_permissions
from app.dependencies import get_current_user
from app.models.user import User


def has_perm(user: User | None, perm: Perm) -> bool:
    if user is None or user.role is None:
        return False
    return perm in role_permissions(user.role.name)


def require(perm: Perm) -> Callable[..., User]:
    """FastAPI dependency factory: yields the user, or 403 if they lack `perm`.

    Usage:
        current_user: User = Depends(require(Perm.STORY_CREATE))
    or, when you only need the gate:
        dependencies=[Depends(require(Perm.ADMIN_USERS))]
    """
    def checker(current_user: User = Depends(get_current_user)) -> User:
        if not has_perm(current_user, perm):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to perform this action.",
            )
        return current_user
    return checker


def authorize_owned(
    user: User,
    resource: Any,
    *,
    own_perm: Perm,
    any_perm: Perm,
    owner_attr: str = "user_id",
) -> None:
    """Authorize an action on a specific resource.

    Allow when the user has the any-resource capability (moderator/admin), OR
    they own the resource and hold the own-resource capability. Otherwise 403.
    """
    if has_perm(user, any_perm):
        return
    owns = getattr(resource, owner_attr, None) == user.id
    if owns and has_perm(user, own_perm):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You don't have permission to perform this action.",
    )
