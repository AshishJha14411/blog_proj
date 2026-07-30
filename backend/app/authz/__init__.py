"""Centralized authorization: one place that defines what each role can do.

Replaces `role.name in ("moderator", "superadmin")` checks scattered across
routes and services — the pattern that let the `"admin"` vs `"superadmin"`
typo silently 403 every creator. Now permissions are named constants, roles
map to permission sets, and every gate goes through `require()` / `has_perm()`.
"""
from app.authz.permissions import Perm, ROLE_PERMS, role_permissions
from app.authz.policy import has_perm, require, authorize_owned

__all__ = ["Perm", "ROLE_PERMS", "role_permissions", "has_perm", "require", "authorize_owned"]
