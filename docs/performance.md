# Performance — story list endpoint

Record of a latency investigation on `GET /api/v1/stories/`, the most-hit read
path in the application.

**Change:** `api:v25` → `api:v26` · **Service:** Cloud Run, `us-central1`
**Client during measurement:** India (relevant — see [Network floor](#network-floor))

---

## Result

| Metric | Before | After | Change |
|---|---|---|---|
| Total request time (warm) | 1.21 s | **0.62 s** | −49% |
| Response payload | 60,924 B | **1,577 B** | −97.4% |
| Time to first byte | 0.854 s | 0.580 s | −32% |
| Transfer time | ~354 ms | ~1 ms | eliminated |
| Server processing | ~440 ms | ~170 ms | −61% |

---

## Method

Latency was decomposed before any change was made, using two measurements.

**1. The endpoint under test:**

```bash
curl -s -o /dev/null \
  -w "ttfb=%{time_starttransfer} total=%{time_total} size=%{size_download}\n" \
  "$BASE/api/v1/stories/?limit=10"
# ttfb=0.854  total=1.208  size=60924
```

**2. A control endpoint that touches no database**, to establish the network floor:

```bash
curl -s -o /dev/null -w "%{time_total}\n" "$BASE/"
# 0.414  0.409  0.424
```

Subtracting gives the breakdown:

```
1.21 s total
├── 0.41 s   network round-trip   (client → us-central1; not addressable in code)
├── 0.44 s   server work          (ttfb − floor)
└── 0.35 s   transfer of 60 KB    (total − ttfb)
```

Roughly 30% of the request was transfer — which directed the work away from the
database query, where it would otherwise have gone by default.

---

## Change 1 — response compression

The API compressed nothing. Confirmed by comparing an explicit `identity` request
against a `gzip` request: identical byte counts, and no `content-encoding` header
on the response.

JSON is highly repetitive (every object repeats the same keys), so it compresses
well. The complication is that this service streams AI story generation over
Server-Sent Events at `/stories/generate/stream`. Starlette's `GZipMiddleware`
also wraps streaming responses, and gzip buffers internally — which delays
individual SSE events and breaks token-by-token delivery.

Compression is therefore applied selectively (`app/main.py`):

```python
class SelectiveGZipMiddleware:
    _EXCLUDED = ("/stream",)

    def __init__(self, app, minimum_size: int = 500):
        self.app = app
        self._gzip = GZipMiddleware(app, minimum_size=minimum_size)

    async def __call__(self, scope, receive, send):
        if scope.get("type") == "http" and not any(
            frag in scope.get("path", "") for frag in self._EXCLUDED
        ):
            await self._gzip(scope, receive, send)
            return
        await self.app(scope, receive, send)   # SSE and WebSockets bypass
```

The decision is keyed on request path, so it is made before a response exists.
`scope["type"] == "http"` excludes WebSockets without a special case.

Verified: JSON responses return `content-encoding: gzip`; the SSE endpoint returns
`content-type: text/event-stream` with no `content-encoding`.

---

## Change 2 — list/detail projection

List responses included each story's **entire** HTML body — roughly 6 KB per
story — to render cards that display three clamped lines of preview text.

List endpoints now return a plain-text excerpt; detail endpoints are unchanged and
still return the full body (`app/services/story.py`):

```python
_EXCERPT_CHARS = 280
_HTML_TAG_RE   = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")

def _excerpt_for_list(items):
    for item in items:
        text = _WHITESPACE_RE.sub(" ", _HTML_TAG_RE.sub(" ", item.content or "")).strip()
        excerpt = text[:_EXCERPT_CHARS] + ("…" if len(text) > _EXCERPT_CHARS else "")
        set_committed_value(item, "content", excerpt)
```

Applied to all four list paths: offset pagination, keyset pagination, search, and
`/stories/me`.

Stripping tags also corrected a rendering defect: the card renders `post.content`
as text, so raw markup was previously visible to users.

Server processing time fell alongside transfer time (~440 ms → ~170 ms), because
serialising 60 KB of JSON through Pydantic is itself CPU work.

### Why `set_committed_value` and not assignment

`item` is a live SQLAlchemy row, and the read path runs a unit of work that
commits at the end of every request (`app/dependencies.py`). Assigning to a mapped
column marks the instance dirty, so a plain `GET` would flush the truncated
excerpt and **permanently overwrite the stored article**.

`set_committed_value()` sets the attribute as though it had been loaded from the
database, producing no change history and therefore nothing to flush.

The same hazard already existed in `_mask_deleted_authors`, which assigned
`user.username` for display. That was safe under the previous read-only sync
session and became unsafe when the read path became transactional. Both call sites
now use `set_committed_value`.

Verified by asserting database state directly:

```bash
BEFORE=$(psql -tAc "SELECT length(content) FROM stories WHERE id='$SID'")
for i in 1 2 3; do curl -s -o /dev/null "$BASE/api/v1/stories/?limit=10"; done
AFTER=$(psql  -tAc "SELECT length(content) FROM stories WHERE id='$SID'")
# 67 -> 67, unchanged
```

---

## Payload reduction, step by step

```
60,924 B   original — full HTML bodies, uncompressed
 8,681 B   after excerpt projection
 2,026 B   after gzip
```

The two changes compound: less text to compress, and what remains compresses well.

---

## Not addressed

<a name="network-floor"></a>

| Item | Measured | Notes |
|---|---|---|
| **Network floor** | ~0.41 s per request | Client in India, service in `us-central1`. Requires a closer region or an edge cache. |
| `GET /stories/search` | ~2.33 s | Uncached full-text search with `ts_rank` ordering. Now the slowest endpoint. |
| `GET /tags/` | ~1.05 s | ≈0.41 s floor plus ~0.6 s server time; not yet profiled. |
| Frontend navigation | not measured | Requires browser-side profiling rather than `curl`. |

**Measurement caveats:** single client location, three warm samples per endpoint,
cold starts excluded, no concurrent load. Sufficient to locate a problem worth 30%
of a request; not a substitute for percentile instrumentation under production
traffic.

---

## Reproducing

```bash
BASE=https://<service-host>

# Network floor — an endpoint that touches no database
curl -s -o /dev/null -w "floor: %{time_total}\n" $BASE/

# Endpoint under test
curl -s -o /dev/null \
  -w "ttfb=%{time_starttransfer} total=%{time_total} size=%{size_download}\n" \
  "$BASE/api/v1/stories/?limit=10"

# Compression check
curl -s -D - -o /dev/null --compressed "$BASE/api/v1/stories/?limit=10" \
  | grep -i content-encoding

# server work   ≈ ttfb − floor
# transfer time ≈ total − ttfb
```
