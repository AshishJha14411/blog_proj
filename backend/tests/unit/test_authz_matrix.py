"""Authorization matrix: every role × every permission, asserted against an
INDEPENDENT expectation table.

Why this shape:
- Routes never ask "is this user a moderator?" — they ask `has_perm(user,
  Perm.X)` through the policy layer (app/authz). So the single source of truth
  for "who can do what" is the role->perm mapping, and THIS is the test that
  pins it down exhaustively: 4 roles × every Perm, plus the anonymous and
  unknown-role edges.
- `EXPECTED` below is written out by hand on purpose — it does NOT import
  ROLE_PERMS's internals. If someone edits the mapping (grants creators
  ADMIN_ADS, say), this matrix fails and forces an intentional decision, instead
  of the change silently redefining the security model.
"""
import pytest

from app.authz import has_perm
from app.authz.permissions import Perm

pytestmark = pytest.mark.unit


# --- The intended policy, restated independently of the implementation. ---
_USER = {Perm.COMMENT_CREATE, Perm.COMMENT_DELETE_OWN, Perm.CREATOR_REQUEST}

_CREATOR = {
    Perm.COMMENT_CREATE,
    Perm.COMMENT_DELETE_OWN,
    Perm.STORY_CREATE,
    Perm.STORY_UPDATE_OWN,
    Perm.STORY_DELETE_OWN,
    Perm.TAG_CREATE,
}

_MODERATOR = _CREATOR | {
    Perm.STORY_MODERATE,
    Perm.COMMENT_MODERATE,
    Perm.MOD_QUEUE,
    Perm.MOD_RESOLVE,
    Perm.ANALYTICS_VIEW,
}

_SUPERADMIN = _MODERATOR | {
    Perm.ADMIN_USERS,
    Perm.ADMIN_ADS,
    Perm.TAG_MANAGE,
}

EXPECTED: dict[str, set[Perm]] = {
    "user": _USER,
    "creator": _CREATOR,
    "moderator": _MODERATOR,
    "superadmin": _SUPERADMIN,
}


class _RoleStub:
    def __init__(self, name):
        self.name = name


class _UserStub:
    """Minimal stand-in — has_perm only ever reads user.role.name."""
    def __init__(self, role_name):
        self.role = _RoleStub(role_name)


# 4 roles × every Perm = the full grid.
_GRID = [(role, perm) for role in EXPECTED for perm in Perm]


@pytest.mark.parametrize("role_name,perm", _GRID, ids=[f"{r}-{p.value}" for r, p in _GRID])
def test_role_permission_matrix(role_name, perm):
    """Each (role, permission) cell must match the intended policy exactly."""
    user = _UserStub(role_name)
    expected = perm in EXPECTED[role_name]
    assert has_perm(user, perm) is expected, (
        f"role '{role_name}' {'should' if expected else 'must NOT'} have {perm.value}"
    )


@pytest.mark.parametrize("perm", list(Perm))
def test_anonymous_has_no_permissions(perm):
    """A None user (anonymous caller) is denied every capability."""
    assert has_perm(None, perm) is False


@pytest.mark.parametrize("perm", list(Perm))
def test_unknown_role_has_no_permissions(perm):
    """An unrecognized role name grants nothing (fail-closed)."""
    assert has_perm(_UserStub("banana"), perm) is False


def test_role_hierarchy_is_strictly_increasing():
    """Sanity on the intended model: user ⊂ creator? No — user has
    CREATOR_REQUEST which creator drops — but moderator ⊃ creator and
    superadmin ⊃ moderator must hold."""
    assert _CREATOR < _MODERATOR < _SUPERADMIN
