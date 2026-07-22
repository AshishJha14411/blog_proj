from datetime import datetime, timezone


def utcnow() -> datetime:
    """Naive UTC now — drop-in replacement for the deprecated datetime.utcnow().

    The schema uses TIMESTAMP WITHOUT TIME ZONE, so values loaded from the DB
    are naive UTC. Keeping "now" naive too means stored values, column
    defaults, and expiry comparisons all stay type-compatible; an aware "now"
    here would raise TypeError against any datetime read back from the DB.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)
