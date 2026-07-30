"""Property-based tests (hypothesis) for the keyset-pagination cursor codec.

Example-based tests check the cases you thought of; property tests check the
ones you didn't. The cursor is an opaque base64 token the client round-trips
back to us, so the invariant that matters is: decode(encode(x)) == x for EVERY
(timestamp, id) pair — if that ever breaks, pagination silently skips or repeats
rows. hypothesis generates hundreds of pairs (odd microseconds, far-future
dates, every UUID shape) to try to break it.
"""
from datetime import datetime

import pytest
from hypothesis import given, settings, strategies as st

from app.services.story import _encode_cursor, _decode_cursor

pytestmark = pytest.mark.unit


@settings(max_examples=300)
@given(
    created_at=st.datetimes(
        min_value=datetime(1970, 1, 1),
        max_value=datetime(2999, 12, 31),
    ),
    story_id=st.uuids(),
)
def test_cursor_roundtrip_is_identity(created_at, story_id):
    token = _encode_cursor(created_at, story_id)
    decoded_at, decoded_id = _decode_cursor(token)
    assert decoded_at == created_at
    assert decoded_id == story_id


@given(garbage=st.text(max_size=60))
def test_decode_rejects_garbage_with_400_not_500(garbage):
    """A tampered/invalid cursor must be a clean 400, never an unhandled crash."""
    from fastapi import HTTPException

    try:
        _decode_cursor(garbage)
    except HTTPException as exc:
        assert exc.status_code == 400
    # A value that happens to decode into a valid ts|uuid is fine too — the
    # point is only that we never raise a non-HTTPException (i.e. never 500).
