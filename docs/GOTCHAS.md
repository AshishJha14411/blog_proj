# Gotchas

Every entry here is a real bug or trap that has already cost debugging time on
this project. They are written symptom-first, because that's how you'll meet
them. **Check here before starting a debugging session.**

---

## Data integrity

### A read request that silently rewrote the database

**Symptom:** story bodies were being replaced by their own truncated excerpts.
No error, no failing test.

**Cause:** a list endpoint helper assigned to a mapped ORM column
(`item.content = excerpt`). That marks the instance dirty, and because reads run
as a unit of work that commits at the seam, the truncated value was flushed back
over the real row. It was harmless under the old sync-session design and became
destructive when reads moved to commit-at-end.

**Fix:** present a value without dirtying the instance.

```python
from sqlalchemy.orm.attributes import set_committed_value
set_committed_value(item, "content", excerpt)
```

**Rule:** never assign to a **mapped column** on a read path. Non-mapped,
response-only attributes (`likes_count`, `is_liked_by_user`) are safe.

**Verify:** `select length(content) from stories where id = …` before and after
repeated list requests — it must not change.

---

## Async SQLAlchemy

### `MissingGreenlet`

**Cause:** an async session has no lazy IO. Touching any relationship that
wasn't loaded raises this.

**Fix:** eager-load everything the response will touch.

```python
select(Story).options(joinedload(Story.user), selectinload(Story.tags))
```

This includes auth dependencies: `has_perm` reads `user.role`, so async auth
deps need `joinedload(User.role)`.

### asyncpg behind PgBouncer

Prepared-statement caching is incompatible with transaction pooling. The engine
sets `statement_cache_size: 0` in `connect_args` when the URL looks pooled.

**The kwarg is `statement_cache_size`, not `prepared_statement_cache_size`** —
the latter is not a valid `create_async_engine` argument in SQLAlchemy 2.0 and
crashes the container at boot. Caught by a zero-traffic canary; it never reached
users, which is exactly why the deploy is canary-first.

### Stale pooled connections

**Symptom:** an intermittent 500 with `SSL connection has been closed unexpectedly`
after a period of idleness.

**Cause:** Neon autosuspends; the pool handed out a dead connection.
**Fix:** `pool_pre_ping=True` and `pool_recycle=300` on both engines.

---

## HTTP / API contract

### The frontend called endpoints that never existed

**Symptom:** the analytics page showed `0` for everything — indistinguishable
from "no data".

**Cause:** it requested `/analytics/series` and `/analytics/ads_ctr`. Those
response *schemas* existed in `schemas/analytics.py`, but **no route was ever
wired to them**. Both 404'd, the page had no `.catch`, so every card rendered its
zero default while the database held real rows.

**Rules:**
- A schema is not an endpoint. Grep `@router.` before believing a path exists.
- Never let a failed fetch render as a plausible empty state. Surface the error.

### Literal routes must precede parameterised ones

`@router.get("/popular")` declared *after* `@router.get("/{story_id}")` makes
FastAPI parse `"popular"` as a UUID and return 422. `/search`, `/me` and
`/popular` all sit above `/{story_id}`.

### Trailing slashes drop the auth header

**Symptom:** an authed request 401s even though the token is valid.

**Cause:** `/me/notifications` (no slash) 307-redirects to `/me/notifications/`,
and browsers **strip `Authorization` on cross-origin redirects**. The retried
request arrives anonymous.

**Fix:** call the exact path. Endpoints with optional auth hide this, because
anonymous still returns 200.

### WebSocket routes are not under `/api/v1`

**Symptom:** support chat silently dead, zero backend errors.

**Cause:** `POST /api/v1/ws/ticket` → 404. WS routers are mounted at the top
level, but the axios instance's `baseURL` includes `/api/v1`, so a relative call
resolved to the versioned path.

**Fix:** build an absolute URL from `API_URL` for anything under `/ws/`.

### A 500 looks like a CORS error

CORS headers are attached by middleware that a crash escapes, so an unhandled
exception reaches the browser as a CORS message. **Read the server log before
touching CORS config.**

### 422 handler crashed into a 500

`RequestValidationError` can carry raw `bytes`, which `json.dumps` refuses. The
problem+json handler must pass the payload through `jsonable_encoder`.

---

## Concurrency

Races here are settled by **database constraints**, not read-then-write:

| Race | Arbiter | Translation |
|---|---|---|
| Concurrent refresh-token rotation | `UNIQUE (jti)` on `token_blacklist` | `IntegrityError` → **401** |
| Double like/bookmark | `UNIQUE (user_id, story_id)` | `IntegrityError` → **409** |
| Concurrent story edit | `row_version` optimistic lock | `StaleDataError` → **409** |

A read-then-write check passes for both racers under load. Let the database
decide, then translate the error.

---

## Frontend state

### A cached placeholder that never refreshed

**Symptom:** the notification badge showed `0` while `GET
/me/notifications/unread_count` returned `{"count": 2}`.

**Cause:** three things combining —
1. the hook set `initialData: 0`, which enters the cache stamped
   `dataUpdatedAt = now`;
2. `app/providers.tsx` sets `staleTime: 30_000`, so that fabricated zero counted
   as **fresh**;
3. the query starts **disabled** (`accessToken` is memory-only and null on load),
   and by the time `AuthInitializer` opened the gate, the zero was still fresh —
   so no fetch was ever issued. With a healthy WebSocket the poll interval is an
   hour.

**Fix:** drop `initialData`; use `data ?? 0` at the render site.

**Why the tests missed it:** every existing test built a `QueryClient` *without*
`staleTime`, which refetches where production doesn't. A cache-sensitive test
must mirror `app/providers.tsx`.

### Don't keep a local tally beside server state

The bell kept `socketUnread` and rendered `socketUnread + polled`. The arriving
notification is already persisted, so the server count includes it — every
notification counted twice once the count refetched. Invalidate the query key
instead; the server is the single source of truth.

### `accessToken` is memory-only by design

Excluded from zustand's `partialize` so XSS can't lift it out of `localStorage`.
Therefore it is `null` on every fresh load and in every new tab until
`AuthInitializer` mints one. Any `enabled: !!accessToken` gate is false on first
render — don't treat that as "not signed in".

---

## Styling (Tailwind v4)

### An undeclared token renders nothing

There is no `tailwind.config.js`; tokens are declared in an `@theme` block in
`app/globals.css`. **Only names declared there generate utilities.** A class
whose token was never declared emits no CSS at all — no error, no warning, the
element is simply unstyled.

This shipped: `bg-background-alt` was used on five card surfaces while
`--color-background-alt` was never declared, so those cards rendered transparent
against the page.

**When a surface looks unexpectedly transparent, check the token exists before
debugging anything else.**

---

## Environment / tooling

### Backend does not hot-reload

Only `./backend/app` is mounted and the server runs without `--reload`. New
endpoint 404s? `docker compose restart backend`.

### Edited backend tests don't reach the container

`backend/tests` isn't mounted. Without the `rm -rf` + `docker compose cp` step
you run stale tests and get results that look real. See `TESTING.md`.

### Container ports differ from host ports

The backend listens on **8080** inside the container; compose publishes it as
**8000** on the host. Container-to-container calls use `http://backend:8080`.

### Turbopack races the Windows bind mount

Frontend 500s with `ENOENT … _buildManifest.js.tmp.*`. Not your code —
`docker compose restart frontend`.

### `npm run gen:api` fails inside the container

It targets `localhost:8000`, which from the frontend container is the *frontend*.
Fetch the spec to a file, copy it in, and point `openapi-typescript` at the file
(`DEVELOPMENT.md`).

### Cypress can't run locally; copy changes break CI

Host `node` aborts with `Illegal instruction`, and in-container the specs'
hardcoded `localhost:8000` doesn't resolve. E2E runs only in CI, and it asserts
on visible strings — so a copy rename passes everything locally and fails there.
`grep -rn "<old string>" frontend/tests/` after any rename.

### `--reporter=basic` is not a valid Vitest reporter here

It fails at startup with a module-resolution error. Use the default.

### Never hand-write `<head>` in the root layout — Cypress injects into it

**Symptom:** every e2e spec fails on page load, before a single assertion runs,
with `Hydration failed because the server rendered HTML didn't match the client`
and a `{" "}` in the diff. Everything local is green: `tsc`, vitest, `next
build`, screenshots, even a DevTools-protocol console probe against plain Chrome.

**Cause:** Cypress proxies the app under test and rewrites the document,
injecting its own instrumentation as `<head> <script>…` — **note the leading
space**. That whitespace becomes a text node and the first child of `<head>`.

If the root layout renders a literal `<head>` in JSX, React *owns and hydrates*
its children by position: it expected your `<script>` first, found whitespace,
and threw. Because Cypress fails a spec on any uncaught application error, the
whole suite dies at page load.

**Fix:** don't render `<head>` at all. Put the script as the first child of
`<body>`; React 19 hoists it into the framework-managed `<head>` on both server
and client, tracking it by identity rather than DOM position, so an injected
sibling can't shift it.

Verified: with the script written into `<body>`, the served HTML still has it
inside `<head>` (before `</head>`), so the no-flash theme behaviour is unchanged.

**Why nothing local catches it:** nothing except Cypress injects into `<head>`.
To reproduce without Cypress, proxy the dev server and inject
`' <script>…</script>'` after `<head>` — the leading space is the whole bug, and
a probe without it reports clean against a known-broken build.

**Rule:** in the App Router, the framework owns `<head>`. Use the `metadata`
export for metadata, and hoisting for scripts. A literal `<head>` in the root
layout is a hydration boundary you don't want.

---

## Production / deploy

### `/healthz` 404s through the public URL

Cloud Run's ingress **reserves `/healthz`** and answers it itself with a
Google-branded HTML 404 — the request never reaches the container. The route
works in-container (the Docker healthcheck passes). Use `/` for external
liveness. Tell the two apart by the body: ours is problem+json.

### Migrations do not run on deploy

Production sets `SKIP_MIGRATIONS=true` (it removes ~10s from cold start). Schema
changes are a separate deliberate step, and **a data backfill written as a
migration will never run** — put it in `backend/scripts/`.

### `--update-env-vars`, never `--set-env-vars`

`--set-env-vars` **replaces** the entire env list, silently deleting the ~13
other literal vars the service needs. The app then boots broken or not at all.

### `CELERY_TASK_ALWAYS_EAGER=true` is required in production

There is no worker (ADR 001). Without the flag, four call sites enqueue to a
broker nobody consumes and **fail silently**: story publish (stays `pending`
forever), signup verification email, webhook delivery, support escalation.

### Long stories were auto-rejected; the moderation queue showed only flagged

Two separate bugs that presented as one "moderation is broken".

**Auto-rejection.** `moderate_content` flagged on the **first** profane word,
and a flag meant `status = rejected`. Profanity is matched per word, so the odds
of a hit rise with word count — meaning the rule was a **length filter wearing a
safety filter's clothes**. Measured against the ten real production stories:
**seven were auto-rejected**, including every story over 1,000 words, while the
highest actual profanity count in any of them was 5.

Fixed in two independent parts (both needed):
- flagged stories are **held** as `pending` for a human, never auto-rejected;
- flagging requires `MODERATION_PROFANITY_THRESHOLD` (default 10) occurrences,
  so the signal is saturation rather than presence.

Flagged content is still never auto-*published* — that safety property is
untouched. See `docs/adr/004-moderation-holds-not-rejects.md`.

> Don't "fix" a future false positive by lowering the threshold or extending
> the whitelist. Both reintroduce the length bias. Add a separate severe-terms
> list that flags at count ≥ 1 instead.

**The queue only ever showed flagged rows.** The route ended with:

```python
items = [i for i in items if getattr(i, "is_flagged", False)]
```

applied *unconditionally*, so "All", "Generated" and "Rejected" were all
silently narrowed to flagged stories — a moderator could not see the queue they
were moderating. `total` was also counted before that drop, so the header
contradicted the list, and pagination showed near-empty pages.

The fix distinguishes **absent** from **empty**: no `status_filter` parameter
keeps the flagged-only default (what a bare `/queue` has always returned), while
`status_filter=""` means the caller explicitly chose "All". The flag filter moved
into the SQL query so `total` and the page describe the same set.

The frontend had a matching bug: `value={params.status || "flagged"}` snapped the
dropdown back to "Flagged" whenever you picked All, because `""` is falsy. `??`
instead of `||`.

> A test "covering" this passed vacuously for the same reason — it asserted
> `all(item["status"] == ... for item in items)` against a list the post-filter
> had emptied, and `all([])` is `True`.

### Support chat connects, accepts your message, and never replies

**Symptom:** the widget opens, the WebSocket handshake succeeds, you send a
message — and nothing comes back. No error in the UI. Eventually (up to 120s)
"The assistant is unavailable."

**Cause:** not the socket. The log line is:

```
ws_support: LLM error: Gemini streaming error: 504 Deadline Exceeded
```

`gemini-flash-latest` degraded to the point of being unusable — **43s to first
streaming chunk** measured directly against the API, and past the 120s
`LLM_TIMEOUT` in production. The handler *does* send an error frame, but only
after the deadline expires, so the UI looks silent rather than broken.

**Fix:** `LLM_MODEL=gemini-flash-lite-latest`. Same measurement: **1.0s to first
chunk**, and a full support answer end-to-end in ~2.5s. It is an env var, so it
takes effect without a rebuild.

Two things that will waste your time here:

- **It is not the token budget.** The obvious theory is that support chat
  inherits `LLM_MAX_TOKENS=8192` (the story-writing budget) and asks for too
  much. Measured: 8192 completed in 43s while 600 *deadlined at 111s*. Output
  length was not the variable — the model was.
- **`gemini-2.5-flash-lite` and `gemini-2.0-flash-lite` both 404** — retired for
  new users. Only the `-latest` alias resolves.

**Also:** `google-generativeai` 0.8.5 rejects `thinking_config` outright
(`Unknown field for GenerationConfig`), so a thinking budget can't be set
without migrating to the newer `google-genai` SDK. Flash-lite defaults to
minimal thinking regardless.

**Testing the socket by hand:** the frame protocol is `{"type":"user","content":…}`
inbound and `{"type":"delta","text":…}` outbound, terminated by `{"type":"done"}`.
Any other inbound `type` gets `"Unknown frame type."` — which is easy to
misread as the chat being broken when it's the test that's wrong.

### Stories stuck in `pending`, emails never sent, and no error anywhere

**Symptom:** you publish a story and it sits at `pending` forever. Signups never
receive a verification email. Nothing in the logs, no exception, no failed
request — the API returns success every time.

**Cause:** nothing consumed the task. `.delay()` succeeded — it enqueued to Redis
— and no worker existed to drain the queue. The enqueue is the part that
reports success, so everything upstream looks healthy.

This was a **local-only** trap created by a config divergence:
`docker-compose.yml` used to default `CELERY_TASK_ALWAYS_EAGER` to `false` while
production sets it to `true`, and the optional `worker` container is only started
by a bare `docker compose up -d`. So:

```
docker compose up -d                    → worker runs, tasks drain, all fine
docker compose up -d backend db redis   → queue fills, nothing ever runs
```

**Fix:** the compose default is now `true`, so local matches production and no
worker is needed. Verify with:

```bash
docker compose exec -T backend python -c \
  "from app.worker import celery_app; print(celery_app.conf.task_always_eager)"
```

**Rule:** when a task's *effect* never happens but nothing errors, check who was
supposed to consume it before debugging the task body.

### A task's retry decorator is a lie in production

**Symptom:** you read `@celery_app.task(autoretry_for=..., max_retries=3,
retry_backoff=4, retry_jitter=True)` and conclude the operation is protected
against transient failures. It isn't.

**Cause:** production runs `task_always_eager=True`. **Eager mode does not
retry** — `self.retry()` raises instead of re-executing. Every retry knob on
every task is inert. `tests/unit/tasks/test_email_task.py` documents this: it
asserts against `Retry` escaping `.apply()`.

**And the failure is invisible.** `task_eager_propagates=False` swallows the
exception so a broken task can't turn a successful write into a 500. Net effect
for email: **signup returns 200, the verification email is never sent, the user
is told nothing, and nothing retries.**

**Rule:** if a task must not be lost, retry **inside** the operation, not via
Celery. `Mailer.send_email` does this — 3 attempts, 1s linear backoff, with
permanent errors (`SMTPRecipientsRefused`, `SMTPAuthenticationError`, …)
short-circuiting so a rejected address doesn't burn a waiting user's time.
See `docs/adr/003-inline-smtp-retry.md`.

**Watch out:** `smtplib.SMTPException` subclasses `OSError`, so a blanket
`except OSError` sweeps permanent failures into a retry loop. Name them
explicitly.

### Vercel builds `main`

Pushing to `dev` deploys no frontend. When reporting a frontend fix, say whether
it is merged — otherwise "fixed" reads as "live" and it isn't.

---

## Schema inspection

- `story_tags` and `story_revisions` use **`stories_id`**, not `story_id`. It
  follows the table name rather than the entity. Documented rather than renamed —
  a migration plus a code sweep for no functional gain — but it will bite you in
  raw SQL.
- `users.email` / `username` uniqueness is enforced by unique **indexes**, not
  table constraints, so `information_schema.table_constraints` shows nothing.
  Check `pg_indexes`. (This nearly got reported as a production integrity hole.)
