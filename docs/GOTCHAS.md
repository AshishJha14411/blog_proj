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
