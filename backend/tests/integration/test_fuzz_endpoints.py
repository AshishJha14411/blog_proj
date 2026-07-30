"""Contract/robustness fuzzing (hypothesis) — the "never a 5xx" guarantee.

This is the hand-rolled stand-in for a schemathesis OpenAPI fuzz run (see
requirements.txt for why schemathesis itself isn't a dep). The contract we
assert is the important half of what a fuzzer gives you: for ANY input a client
can send, a well-behaved API answers with a 2xx or a 4xx — never a 5xx. A 500
means an unhandled edge (the class of bug that produced our validation-error
crash). hypothesis throws hundreds of hostile query/path values at the public
read surface and proves every one is handled.
"""
import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

pytestmark = pytest.mark.integration

# hypothesis drives many examples through one function-scoped `client` — that's
# intentional (read-only GETs), so silence the shared-fixture health check.
_FUZZ = settings(
    max_examples=60,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)


@_FUZZ
@given(q=st.text(min_size=1, max_size=64))
def test_search_never_500s(client, q):
    resp = client.get("/stories/search", params={"q": q})
    assert resp.status_code < 500, f"q={q!r} -> {resp.status_code}"


@_FUZZ
@given(
    limit=st.integers(min_value=-(10**6), max_value=10**6),
    offset=st.integers(min_value=-(10**6), max_value=10**6),
    tag=st.text(max_size=32),
    cursor=st.text(max_size=48),
)
def test_list_never_500s(client, limit, offset, tag, cursor):
    resp = client.get(
        "/stories/",
        params={"limit": limit, "offset": offset, "tag": tag, "cursor": cursor},
    )
    assert resp.status_code < 500, (
        f"limit={limit} offset={offset} tag={tag!r} cursor={cursor!r} -> {resp.status_code}"
    )


@_FUZZ
@given(story_id=st.from_regex(r"[A-Za-z0-9._~-]{1,48}", fullmatch=True))
def test_story_detail_bad_id_never_500s(client, story_id):
    # URL-safe garbage (raw control chars are rejected by the HTTP client
    # itself, not the server, so they aren't a server contract concern). A
    # non-UUID path segment must be a clean 404/422, never a 5xx.
    resp = client.get(f"/stories/{story_id}")
    assert resp.status_code < 500, f"story_id={story_id!r} -> {resp.status_code}"
