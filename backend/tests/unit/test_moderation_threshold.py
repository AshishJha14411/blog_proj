"""Profanity threshold: saturation, not presence.

/** WHY THIS EXISTS: flagging on the FIRST profane word made length the real
    filter. Measured against the 10 real stories in production, the old rule
    flagged 7 of them — including every story over 1,000 words — while the
    highest actual count in any of them was 5. The moderation signal was
    firing on ordinary fiction. **/
"""
import pytest

from app.services.moderation import count_profane_words, moderate_content

pytestmark = pytest.mark.unit

CLEAN = "The lighthouse keeper watched the storm roll in over the grey water."
# `shit` is not whitelisted; `damn`/`hell` are (ordinary in prose).
SWEAR = "shit"


def _text_with(n: int) -> str:
    """A realistic-length passage carrying exactly `n` profane words."""
    return " ".join(([CLEAN] * 40) + ([SWEAR] * n))


def test_counts_occurrences_not_distinct_words():
    """One word used ten times is a stronger signal than ten used once."""
    assert count_profane_words([" ".join([SWEAR] * 10)]) == 10


def test_whitelisted_fiction_words_do_not_count():
    """"damn"/"hell" are ordinary in prose and must not accumulate toward the
    threshold, or period and horror fiction trips it on style alone."""
    assert count_profane_words(["Damn it to hell, the bastard is bloody late."]) == 0


def test_below_threshold_is_not_flagged():
    flagged, _ = moderate_content([_text_with(5)])
    assert flagged is False, "5 occurrences is fiction, not a policy breach"


def test_at_threshold_is_flagged():
    flagged, cats = moderate_content([_text_with(10)])
    assert flagged is True
    # The reason carries the count so a moderator can judge without re-reading.
    assert "10" in cats[0]


def test_long_clean_story_is_not_flagged_however_long():
    """REGRESSION: the core bug. Length alone must never trigger moderation.

    Under the old rule a story like this was flagged the moment it contained a
    single rude word anywhere in several thousand words.
    """
    long_story = " ".join([CLEAN] * 600)          # ~7,000 words, no profanity
    assert count_profane_words([long_story]) == 0
    assert moderate_content([long_story])[0] is False

    # And one stray swear in a long story still must not flag it.
    assert moderate_content([long_story + " " + SWEAR])[0] is False


def test_threshold_is_configurable(monkeypatch):
    """Tunable without a redeploy — the right number is an operational call."""
    import app.services.moderation as mod
    monkeypatch.setattr(mod.settings, "MODERATION_PROFANITY_THRESHOLD", 3, raising=False)
    assert moderate_content([_text_with(2)])[0] is False
    assert moderate_content([_text_with(3)])[0] is True
