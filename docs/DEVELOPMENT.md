# Development guide

Everything needed to get productive, with the exact commands that work in this
setup. Every command here has been run; where something *doesn't* work in a
given environment, that's called out rather than left for you to discover.

---

## Prerequisites

Docker Desktop is the only hard requirement — the whole stack runs in compose.

Node and Python on the host are optional and, on the machine this was developed
on, host `node`/`npx` crash with `Illegal instruction`. **Run tooling through
`docker compose exec` rather than on the host.**

---

## First run

```bash
cp .env.example .env          # then fill in the values (see below)
docker compose up -d
```

| Service | Host | Inside the compose network |
|---|---|---|
| Frontend | http://localhost:3000 | `http://frontend:3000` |
| Backend | http://localhost:8000 | **`http://backend:8080`** |
| Postgres | localhost:5432 | `db:5432` |
| Redis | localhost:6379 | `redis:6379` |

**The backend listens on 8080 inside the container** and compose publishes it as
8000 on the host. Getting this wrong is the usual cause of "connection refused"
from one container to another.

Verify it came up:

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/          # 200
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3000/          # 200
curl -s http://localhost:8000/docs > /dev/null && echo "swagger ok"
```

> Don't health-check `/healthz` through a deployed URL — Cloud Run reserves that
> path and answers it itself. It works in-container. Use `/` externally.

### Environment

`.env.example` lists the required keys: `POSTGRES_USER`, `POSTGRES_PASSWORD`,
`POSTGRES_DB`, `SECRET_KEY`, `JWT_SECRET_KEY`, `GOOGLE_API_KEY`,
`ADMIN_USERNAME`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`.

`SECRET_KEY` and `JWT_SECRET_KEY` are **separate on purpose** — JWTs are signed
with the dedicated one.

⚠ `backend/.env` points at **production**. `docker compose` overrides it to the
local database, but any command run outside compose (notably alembic) will hit
production unless you pin the URL explicitly. See `DEPLOY.md`.

### Seed data

```bash
docker compose exec -T backend python -m app.seed
```

Creates the roles and an admin account from the `ADMIN_*` env vars. CI runs this
before e2e.

### Background tasks run inline — locally too

`CELERY_TASK_ALWAYS_EAGER` defaults to **`true`** in `docker-compose.yml`, so
`.delay()` executes the task immediately, in the calling process. **There is no
worker, and you don't need one.** This matches production exactly (ADR 001).

> **This default was flipped for a reason.** It used to be `false`, so local dev
> ran the *opposite* semantics to production and the behaviour depended on
> whether the optional `worker` container was up:
>
> ```
> docker compose up -d                    → worker runs, tasks drain
> docker compose up -d backend db redis   → NOTHING consumes the queue
> ```
>
> In the second case every `.delay()` enqueued to Redis and sat there forever.
> Published stories stayed **`pending`**, verification emails were **never
> sent**, and nothing errored — because the *enqueue* succeeded. It looks
> exactly like a broken app, and it is not a bug that exists in production.
>
> If you see stories stuck in `pending` or emails never arriving locally, check
> this setting before you debug anything else.

The `worker` service still exists in compose for exercising the real worker path
(Celery's `autoretry_for` only does anything with a worker). Opt in explicitly:

```bash
CELERY_TASK_ALWAYS_EAGER=false docker compose up -d      # worker included
```

Just remember that configuration is **not** what production runs.

---

## Daily workflow

### Reloading

- **Frontend hot-reloads.** `./frontend` is bind-mounted.
- **Backend does not.** Only `./backend/app` is mounted and the server runs
  without `--reload`, so:

```bash
docker compose restart backend     # after ANY backend change
```

Forgetting this is the most common source of "my new endpoint 404s".

### Running tests

**Backend** — note the copy step; it is not optional:

```bash
docker compose exec --user root -T backend sh -c 'rm -rf /app/tests'
docker compose cp ./backend/tests backend:/app/tests
docker compose exec -T -e TEST_DB_BASE="postgresql://test_user:test_password@db:5432/quill_test" \
  -e NO_NETWORK=0 backend python -m pytest tests/ -m "not e2e" -q
```

Only `backend/app` is bind-mounted, so edited test files never reach the
container on their own — without the copy you are running stale tests. `--user
root` is needed because the app user can't delete `/app/tests`.

**Frontend**

```bash
docker compose exec -T frontend npx vitest run
docker compose exec -T frontend npx tsc --noEmit
docker compose exec -T frontend npx vitest run tests/unit/hooks/useUnreadNotifications.test.ts
```

**Baseline: backend 403, frontend 89, `tsc` clean.** Anything less is a
regression you introduced.

Full detail — including why Cypress can't run locally — in `TESTING.md`.

### Regenerating API types after a backend schema change

The `npm run gen:api` script targets `localhost:8000`, which doesn't resolve
from inside the frontend container. Use the file form:

```bash
curl -s http://localhost:8000/openapi.json -o /tmp/openapi.json
docker compose cp /tmp/openapi.json frontend:/tmp/openapi.json
docker compose exec -T frontend npx openapi-typescript /tmp/openapi.json -o lib/api-types.ts
docker compose exec -T frontend npx tsc --noEmit
```

### Inspecting the local database

```bash
docker compose exec -T backend python -c "
from sqlalchemy import text
from app.core.database import SessionLocal
db = SessionLocal()
print(db.execute(text('select count(*) from stories')).scalar())
db.close()
"
```

---

## Migrations

```bash
# current head
ls backend/alembic/versions/

# create (autogenerate, then READ the output before trusting it)
docker compose exec -T backend python -m alembic revision --autogenerate -m "description"

# apply locally
docker compose exec -T backend python -m alembic upgrade head
```

The chain is linear — never branch it. Production runs with
`SKIP_MIGRATIONS=true`, so migrations there are a separate deliberate step
(`DEPLOY.md`), and **data backfills must be scripts, not migrations**, or they
will never run in production.

---

## Operational scripts

`backend/scripts/` holds reviewed, idempotent production actions. `scripts/` is
**not** bind-mounted, so copy it in:

```bash
docker compose exec --user root -T backend rm -rf /app/scripts
docker cp backend/scripts "$(docker compose ps -q backend):/app/scripts"

# always dry-run first
docker compose exec -T -e DATABASE_URL="<url>" -w /app backend \
  python -m scripts.backfill_story_tags --dry-run
```

| Script | Purpose |
|---|---|
| `backfill_story_tags.py` | Derive tags from genre for stories created before that behaviour existed |
| `grant_superadmin.py` | Promote or seed an operator account (`--oauth` for Google sign-in) |
| `delete_users.py` | Remove accounts so an email can be re-registered; `--reassign-to` moves authored stories to another user first |

**Deleting a user is not just a `DELETE`.** `users.id` is referenced by ~19
tables and the right handling differs per column. `delete_users.py` discovers
the referencing columns from the catalog — so a newly added table can't be
silently missed — and dispatches by what the column *means*:

| Kind | Example | Handling with `--reassign-to` |
|---|---|---|
| Authored content | `stories`, `story_revisions`, `comments` | **Reassigned** — deleting a test account must not remove published work |
| Interactions | `likes`, `bookmarks` | **Reassigned row by row.** These carry `UNIQUE (user_id, story_id)`, so a blind update raises `IntegrityError` the moment the new owner already interacted with that story. Colliding rows are dropped instead — nothing is lost, the engagement is already represented by the row the target owns |
| Nullable references | `view_history.user_id`, `notifications.actor_id` | **Nulled** — the row is someone else's record and should survive, just without pointing at a user who no longer exists |
| Account-owned | `oauth_accounts`, tokens, OTPs | **Deleted** — meaningless without the account |

Add a script here for any one-off production change instead of running raw SQL —
it makes the action reviewable, repeatable and diffable.

---

## Branching and CI

- Work on `dev`. `main` is protected and is what deploys.
- **Vercel builds `main`** — pushing to `dev` deploys no frontend.
- The backend deploys manually via `DEPLOY.md` (canary first).

CI (`.github/workflows/ci.yml`) runs on pushes to `main`/`dev`/`testBranch` and
PRs to `main`:

| Job | What it does |
|---|---|
| Secret Scan | gitleaks — fails on any committed secret |
| Backend Tests | `pytest -v -m "not e2e"` against real Postgres + Redis services |
| Frontend Tests | `npm test -- --run` (vitest) |
| Image Scan | Trivy (non-blocking) |
| E2E | Cypress against a booted stack — needs backend + frontend jobs green |

**E2E only runs in CI.** Copy changes that break a Cypress assertion pass every
local check and fail there.

---

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Frontend 500, `ENOENT … _buildManifest.js.tmp` | Turbopack racing the Windows bind mount. `docker compose restart frontend` |
| New endpoint 404s | Backend doesn't hot-reload — `docker compose restart backend` |
| Test edits seem ignored | You skipped the `docker compose cp ./backend/tests` step |
| `MissingGreenlet` | An async read touched an unloaded relationship — add `joinedload`/`selectinload` |
| 401 on an authed call that should work | Check the trailing slash (`/me/notifications/`) — a 307 drops the auth header |
| CORS error in the browser | Usually a real 500: a crash escapes before CORS headers are attached. Read the server log |
| `connection refused` between containers | Use service names and the *internal* port: `http://backend:8080` |
| Alembic hit the wrong database | `backend/.env` points at production — pin `MIGRATION_DATABASE_URL` |
| **Stories stuck in `pending`** | Nothing consumed the task. Check `CELERY_TASK_ALWAYS_EAGER` is `true` (it's the compose default) — if it's `false` you need the `worker` container running |
| **Emails never arrive locally** | Same cause as above. If eager mode *is* on, check the send actually happened: the task logs `email sent (message_id=…)` |
| Signup feels slow | It sends **two** emails (verification + OTP) inline. Bounded by `SMTP_TOTAL_BUDGET_SECONDS` (default 12s) |
| Signing up with Google sends no email | Correct — `handle_google_login` creates the account already `is_verified=True`. Google proved the address; there is nothing to verify. Use the email/password form to test the mail lifecycle |
| Support chat connects but never replies | The LLM is deadlining, not the socket. Check `LLM_MODEL` is `gemini-flash-lite-latest` — plain `flash` measured 43s to first token and 504s in production |

More, with the full stories behind them, in `GOTCHAS.md`.
