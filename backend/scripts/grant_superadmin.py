"""Grant superadmin to an account, creating it first if it doesn't exist.

Superadmin is the only role that can reach the moderation queue, analytics and
the admin routes, and there is deliberately no self-service path to it — the
signup flow always lands a new account on the default role. This script is that
path, kept in the repo so promoting an operator is a reviewed, repeatable action
rather than an ad-hoc `UPDATE` typed into a psql prompt against production.

If the account is missing it is created **verified** (an operator can't wait on
an email loop) with a generated 24-character password that is printed exactly
once. Change it, or use the password-reset flow, after first sign-in.

**For a Google sign-in operator, pass `--oauth`.** `handle_google_login` looks
up an existing user *by email* before creating one, and links the Google
identity to whatever it finds — so a row seeded here is adopted on first sign-in
with its role intact. Without seeding, Google login would create the account
fresh on the hardcoded `user` role instead. `--oauth` sets an unguessable random
password that is never printed, because the account will never sign in with one;
`password_hash` is NOT NULL, so it cannot simply be left empty.

Usage:

    python -m scripts.grant_superadmin someone@example.com --dry-run
    python -m scripts.grant_superadmin someone@example.com
    python -m scripts.grant_superadmin someone@example.com --oauth
    python -m scripts.grant_superadmin someone@example.com --username custom-name

    # against another database (e.g. production, from a local shell)
    DATABASE_URL=postgresql://... python -m scripts.grant_superadmin someone@example.com
"""
from __future__ import annotations

import argparse
import os
import re
import secrets
import string
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.role import Role  # noqa: E402
from app.models.user import User  # noqa: E402
from app.utils.security import hash_password  # noqa: E402

SUPERADMIN_ROLE = "superadmin"
_PASSWORD_ALPHABET = string.ascii_letters + string.digits + "!@#$%^&*-_"


def _sync_url(url: str) -> str:
    return re.sub(r"\+(asyncpg|aiosqlite)://", "://", url)


def _username_from_email(email: str) -> str:
    """Derive a username that satisfies the same shape the signup flow uses."""
    base = re.sub(r"[^a-z0-9_]", "", email.split("@")[0].lower().replace(".", "_"))
    return (base or "admin")[:24]


def _unique_username(session: Session, candidate: str) -> str:
    """Append a short random suffix if the username is taken."""
    if not session.query(User).filter(User.username == candidate).first():
        return candidate
    return f"{candidate[:16]}_{secrets.token_hex(4)}"


def grant(session: Session, email: str, *, username: str | None = None,
          oauth: bool = False, dry_run: bool = False) -> tuple[str, str | None]:
    """Ensure `email` exists and holds the superadmin role.

    Returns `(action, generated_password)` where action is one of
    `created` / `promoted` / `unchanged`. The password is None when nothing was
    created, or when `oauth` is set and it would never be used.
    """
    email = email.strip().lower()

    role = session.query(Role).filter(Role.name == SUPERADMIN_ROLE).first()
    if role is None:
        raise SystemExit(f"role {SUPERADMIN_ROLE!r} not found — is this the right database?")

    user = session.query(User).filter(User.email == email).first()

    if user is None:
        password = "".join(secrets.choice(_PASSWORD_ALPHABET) for _ in range(24))
        user = User(
            email=email,
            username=_unique_username(session, username or _username_from_email(email)),
            password_hash=hash_password(password),
            role_id=role.id,
            # An operator account can't complete the emailed verification loop
            # before it's needed, and unverified accounts are gated out of the
            # very routes this script exists to grant.
            is_verified=True,
            is_disabled=False,
        )
        if not dry_run:
            session.add(user)
            session.commit()
        print(f"  created {email} (username {user.username!r}) as {SUPERADMIN_ROLE}")
        if oauth:
            print("  sign-in method: Google — the first Google login matches this")
            print("  row by email, links the identity, and keeps the superadmin role")
            return "created", None
        return "created", password

    if user.role_id == role.id:
        print(f"  {email} is already {SUPERADMIN_ROLE} — nothing to do")
        return "unchanged", None

    previous = session.query(Role).filter(Role.id == user.role_id).first()
    user.role_id = role.id
    if user.is_disabled:
        # Promoting a disabled account would grant a role nobody can sign into.
        user.is_disabled = False
        print(f"  re-enabled {email} (was disabled)")
    if not dry_run:
        session.commit()
    print(f"  promoted {email}: {previous.name if previous else '?'} -> {SUPERADMIN_ROLE}")
    return "promoted", None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("email", help="email address to grant superadmin to")
    parser.add_argument("--username", default=None,
                       help="username to use if the account must be created")
    parser.add_argument("--oauth", action="store_true",
                       help="account signs in with Google; don't print a password")
    parser.add_argument("--dry-run", action="store_true",
                       help="print what would change, write nothing")
    parser.add_argument("--database-url", default=None)
    args = parser.parse_args()

    url = args.database_url or os.environ.get("DATABASE_URL")
    if not url:
        from app.core.config import settings
        url = settings.DATABASE_URL

    engine = create_engine(_sync_url(url))
    print(f"{'DRY RUN — ' if args.dry_run else ''}granting {SUPERADMIN_ROLE}")
    with Session(engine) as session:
        action, password = grant(session, args.email, username=args.username,
                                 oauth=args.oauth, dry_run=args.dry_run)
        if args.dry_run:
            session.rollback()

    if password and not args.dry_run:
        print("\n  ---------------------------------------------------------")
        print(f"  TEMPORARY PASSWORD: {password}")
        print("  Shown once. Share it over a secure channel and change it")
        print("  after first sign-in.")
        print("  ---------------------------------------------------------")
    elif password:
        print("\n  (a password would be generated and printed here)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
