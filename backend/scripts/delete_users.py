"""Delete user accounts, optionally reassigning the content they authored.

Signup is gated on a unique email, so re-testing the signup -> verify -> publish
lifecycle with an address that already exists is impossible without removing the
old row first. This script is that removal, kept in the repo so a destructive
production action is reviewable and repeatable rather than typed at a psql
prompt at speed.

`users.id` is referenced by ~19 tables. The script discovers them from the
catalog instead of hardcoding a list, because a missed foreign key is either a
failed delete or an orphaned row, and the set grows as the schema does. Each
referencing column is then handled by what it means:

  * authored content (`stories`, `story_revisions`)  -> reassigned when
    `--reassign-to` is given, so deleting an account doesn't quietly remove
    published work; otherwise deleted with the user.
  * NULLABLE references (e.g. `notifications.actor_id`, `flags.resolved_by`)
    -> set to NULL. The row is somebody else's record and should survive; it
    just no longer points at a user who exists.
  * everything else (likes, bookmarks, sessions, tokens...) -> deleted. It
    belongs to the account and has no meaning without it.

Usage:

    python -m scripts.delete_users a@x.com b@y.com --dry-run
    python -m scripts.delete_users a@x.com --reassign-to owner@x.com --dry-run
    python -m scripts.delete_users a@x.com --reassign-to owner@x.com

    DATABASE_URL=postgresql://... python -m scripts.delete_users ...
"""
from __future__ import annotations

import argparse
import os
import re
import sys

from sqlalchemy import create_engine, text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Columns that represent authored content rather than account data. These move
# to the new owner wholesale — none of them carry a per-user unique constraint.
AUTHORED = {
    ("stories", "user_id"),
    ("story_revisions", "user_id"),
    ("comments", "user_id"),
}

# /** Interactions are ALSO the user's records, but they carry
#     UNIQUE(user_id, story_id) — "one like per user per story", enforced by the
#     database. A blind reassign therefore raises IntegrityError the moment the
#     new owner already interacted with the same story.
#
#     So they are moved row by row: reassigned where the target has no existing
#     row, deleted where it does. Deleting the collision loses nothing — the
#     engagement is already represented by the row the target owns. The mapping
#     is {table: conflicting column}. **/
INTERACTIONS = {
    ("likes", "user_id"): "story_id",
    ("bookmarks", "user_id"): "story_id",
}

FK_SQL = """
select tc.table_name, kcu.column_name, c.is_nullable
from information_schema.table_constraints tc
join information_schema.key_column_usage kcu
     on kcu.constraint_name = tc.constraint_name
join information_schema.constraint_column_usage ccu
     on ccu.constraint_name = tc.constraint_name
join information_schema.columns c
     on c.table_name = tc.table_name and c.column_name = kcu.column_name
where tc.constraint_type = 'FOREIGN KEY'
  and ccu.table_name = 'users' and ccu.column_name = 'id'
order by tc.table_name, kcu.column_name
"""


def _sync_url(url: str) -> str:
    return re.sub(r"\+(asyncpg|aiosqlite)://", "://", url)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("emails", nargs="+", help="email address(es) to delete")
    ap.add_argument("--reassign-to", default=None,
                    help="email of the account that inherits authored stories")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--database-url", default=None)
    args = ap.parse_args()

    url = args.database_url or os.environ.get("DATABASE_URL")
    if not url:
        from app.core.config import settings
        url = settings.DATABASE_URL

    engine = create_engine(_sync_url(url))
    print(f"{'DRY RUN — ' if args.dry_run else ''}deleting {len(args.emails)} account(s)")

    with engine.begin() as c:
        fks = c.execute(text(FK_SQL)).fetchall()

        new_owner = None
        if args.reassign_to:
            new_owner = c.execute(text("select id from users where lower(email)=lower(:e)"),
                                  {"e": args.reassign_to}).scalar()
            if not new_owner:
                raise SystemExit(f"--reassign-to: no such user {args.reassign_to!r}")
            print(f"  authored content -> {args.reassign_to} ({new_owner})\n")

        totals = {"reassigned": 0, "nulled": 0, "deleted": 0, "users": 0}

        for email in args.emails:
            uid = c.execute(text("select id from users where lower(email)=lower(:e)"),
                            {"e": email}).scalar()
            if not uid:
                print(f"  {email}: not found — skipping")
                continue
            print(f"  {email}")

            for tbl, col, nullable in fks:
                n = c.execute(text(f"select count(*) from {tbl} where {col} = :u"),
                              {"u": uid}).scalar()
                if not n:
                    continue

                if (tbl, col) in AUTHORED and new_owner:
                    print(f"      reassign  {tbl}.{col:22} {n}")
                    if not args.dry_run:
                        c.execute(text(f"update {tbl} set {col} = :new where {col} = :u"),
                                  {"new": new_owner, "u": uid})
                    totals["reassigned"] += n
                elif (tbl, col) in INTERACTIONS and new_owner:
                    other = INTERACTIONS[(tbl, col)]
                    dupes = c.execute(text(
                        f"select count(*) from {tbl} t where t.{col} = :u and exists "
                        f"(select 1 from {tbl} x where x.{col} = :new and x.{other} = t.{other})"
                    ), {"u": uid, "new": new_owner}).scalar()
                    movable = n - dupes
                    if movable:
                        print(f"      reassign  {tbl}.{col:22} {movable}")
                        totals["reassigned"] += movable
                    if dupes:
                        print(f"      DELETE    {tbl}.{col:22} {dupes}"
                              f"  (target already has this {other})")
                        totals["deleted"] += dupes
                    if not args.dry_run:
                        # Drop the collisions first, then move what's left.
                        c.execute(text(
                            f"delete from {tbl} t where t.{col} = :u and exists "
                            f"(select 1 from {tbl} x where x.{col} = :new and x.{other} = t.{other})"
                        ), {"u": uid, "new": new_owner})
                        c.execute(text(f"update {tbl} set {col} = :new where {col} = :u"),
                                  {"new": new_owner, "u": uid})
                elif nullable == "YES":
                    print(f"      null out  {tbl}.{col:22} {n}")
                    if not args.dry_run:
                        c.execute(text(f"update {tbl} set {col} = NULL where {col} = :u"),
                                  {"u": uid})
                    totals["nulled"] += n
                else:
                    print(f"      DELETE    {tbl}.{col:22} {n}")
                    if not args.dry_run:
                        c.execute(text(f"delete from {tbl} where {col} = :u"), {"u": uid})
                    totals["deleted"] += n

            # story_tags hangs off stories, not users — clean links for any story
            # that is about to be deleted (i.e. when not reassigning).
            if not new_owner:
                orphan = c.execute(text(
                    "select count(*) from story_tags st join stories s on s.id = st.stories_id "
                    "where s.user_id = :u"), {"u": uid}).scalar()
                if orphan:
                    print(f"      DELETE    story_tags (via stories)  {orphan}")
                    if not args.dry_run:
                        c.execute(text(
                            "delete from story_tags where stories_id in "
                            "(select id from stories where user_id = :u)"), {"u": uid})

            print(f"      DELETE    users                      1")
            if not args.dry_run:
                c.execute(text("delete from users where id = :u"), {"u": uid})
            totals["users"] += 1

        if args.dry_run:
            # Everything above ran inside this transaction; roll it back.
            c.rollback()

    print(f"\n{totals['users']} user(s), {totals['reassigned']} row(s) reassigned, "
          f"{totals['nulled']} nulled, {totals['deleted']} deleted"
          f"{' — NOTHING WRITTEN' if args.dry_run else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
