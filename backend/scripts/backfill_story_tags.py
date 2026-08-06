"""Backfill tags for stories created before the genre-to-tag conversion existed.

Every story generated through the AI path landed with **zero** tags: the
generator collected a `genre` but, unlike `create_story`, never resolved it into
`Tag` rows. Production ended up with 0 rows in `tags` and 0 in `story_tags`, so
the tag filter had nothing to filter on and no story card rendered a chip.

`finalize_generated_story` now converts genre into tags for every new story.
This script applies the same conversion to the rows that predate the fix.

Idempotent and additive:
  * only stories with **no** tags are touched, so re-running is a no-op;
  * tags are get-or-create through the same `resolve_tags` used at write time,
    so no duplicate `tags` rows appear;
  * nothing is deleted and no story column is modified.

Usage (defaults to the app's configured database):

    python -m scripts.backfill_story_tags --dry-run
    python -m scripts.backfill_story_tags

    # against another database (e.g. production, from a local shell)
    DATABASE_URL=postgresql://... python -m scripts.backfill_story_tags
"""
from __future__ import annotations

import argparse
import os
import re
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, selectinload

# Allow `python scripts/backfill_story_tags.py` as well as `-m scripts...`.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.stories import Story  # noqa: E402
from app.services.story import resolve_tags, tags_from_genre  # noqa: E402


def _sync_url(url: str) -> str:
    """Strip any async driver suffix — this script runs sync SQLAlchemy."""
    return re.sub(r"\+(asyncpg|aiosqlite)://", "://", url)


def backfill(session: Session, *, dry_run: bool = False) -> tuple[int, int]:
    """Attach genre-derived tags to every story that currently has none.

    Returns `(stories_updated, stories_skipped)`.
    """
    stories = session.query(Story).options(selectinload(Story.tags)).all()
    updated = skipped = 0

    for story in stories:
        if story.tags:
            skipped += 1
            continue

        names = tags_from_genre(story.genre)
        if not names:
            # No genre, or a genre that normalises to nothing. Leave it alone
            # rather than inventing a tag the author never chose.
            skipped += 1
            continue

        print(f"  {story.title[:44]:46} {story.genre!r:24} -> {names}")
        if not dry_run:
            story.tags = resolve_tags(session, names)
        updated += 1

    if dry_run:
        session.rollback()
    else:
        session.commit()
    return updated, skipped


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                       help="print what would change, write nothing")
    parser.add_argument("--database-url", default=None,
                       help="override the database URL (else DATABASE_URL / app settings)")
    args = parser.parse_args()

    url = args.database_url or os.environ.get("DATABASE_URL")
    if not url:
        from app.core.config import settings
        url = settings.DATABASE_URL

    engine = create_engine(_sync_url(url))
    print(f"{'DRY RUN — ' if args.dry_run else ''}backfilling story tags")
    with Session(engine) as session:
        updated, skipped = backfill(session, dry_run=args.dry_run)

    print(f"\n{updated} stor{'y' if updated == 1 else 'ies'} tagged, {skipped} skipped "
          f"(already tagged or no usable genre){' — nothing written' if args.dry_run else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
