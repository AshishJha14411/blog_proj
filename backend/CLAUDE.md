# backend/CLAUDE.md — rules for backend work

Scoped rules for `backend/`. Read `../CLAUDE.md` first for project-wide rules.
Schema, endpoint tables and migration chain live in `README.md` (this folder).

---

## Layering — where code goes

```
routes/    HTTP only. Validate input, call a service, serialise the result.
           No queries, no business rules, no commits.
services/  Business logic AND the transaction boundary. Commits happen here.
models/    SQLAlchemy ORM. Columns, relationships, constraints.
schemas/   Pydantic. This IS the API contract — it generates the OpenAPI doc
           the frontend's types are built from.
authz/     Perm enum + ROLE_PERMS matrix.
tasks/     Celery tasks. In production these run INLINE (ADR 001).
```

If you find yourself writing `db.query(...)` in a route, stop — it belongs in a
service.

---

## The async/sync split — the thing most likely to bite you

**Reads are `async`. Writes are `sync`.** This is deliberate, not an accident of
migration.

Writes stay synchronous because they must keep the ordering
`db.commit()` → `db.refresh()` → `task.delay()`. Since tasks execute inline in
production, an enqueue before the commit would run against a row that isn't
visible yet.

### Async has no lazy IO

Touching an unloaded relationship inside an async session raises
`MissingGreenlet`. Every relationship you access must be eager-loaded:

```python
select(Story)
  .options(joinedload(Story.user), selectinload(Story.tags))
```

This applies to auth dependencies too — `has_perm` reads `user.role`, so async
auth deps must `joinedload(User.role)`.

### Never assign to a mapped column during a read

A read path is a unit of work that commits at the seam. Assigning to a mapped
column marks the instance dirty and **writes it back**.

```python
# WRONG — silently destroys the stored story body
item.content = excerpt

# RIGHT — presents a value without making the instance dirty
from sqlalchemy.orm.attributes import set_committed_value
set_committed_value(item, "content", excerpt)
```

This shipped once and was corrupting data in production. `_excerpt_for_list` and
`_mask_deleted_authors` in `services/story.py` are the reference implementations.

Attributes that are **not** mapped columns (`likes_count`, `is_liked_by_user`)
are safe to assign directly — they exist only on the response schema.

---

## Authorization

Never check role names inline. Use the matrix:

```python
from app.authz import Perm, has_perm, require

# In a service:
if not has_perm(current_user, Perm.STORY_CREATE):
    raise HTTPException(403, "...")

# As a route dependency (gate object is module-level so tests can override it):
can_create_story = require(Perm.STORY_CREATE)
```

Adding a capability means adding a `Perm` member and granting it in
`ROLE_PERMS` — one place, and `tests/unit/test_authz_matrix.py` covers it.

---

## Adding an endpoint — checklist

1. **Schema first** in `schemas/` — it becomes the public contract.
2. **Service function** in `services/` with the business logic.
3. **Route** in `routes/`, thin, with an explicit `response_model`.
4. **Path-ordering:** literal paths MUST be declared *before* parameterised ones.
   `@router.get("/popular")` after `@router.get("/{story_id}")` makes FastAPI
   parse `"popular"` as a UUID and return 422. `/search`, `/me` and `/popular`
   all sit above `/{story_id}` for this reason.
5. **Authorize it** — default to requiring a permission; make public access the
   conscious exception.
6. **Test it** (`docs/TESTING.md`).
7. **Regenerate frontend types** — see `frontend/CLAUDE.md`. A new endpoint that
   the frontend can't see is half-shipped.
8. **Document it** in this folder's `README.md` API table.

---

## Migrations

The chain is **linear — never branch it**. Check the current head before adding:

```bash
ls backend/alembic/versions/
```

Rules learned the hard way:

- **Production runs with `SKIP_MIGRATIONS=true`.** Migrations do NOT run on
  deploy. They are a separate, deliberate step — see `docs/DEPLOY.md`.
- Run migrations against production with `MIGRATION_DATABASE_URL` pinned to the
  **direct** (unpooled) Neon URL. `backend/.env` points at production, and
  compose overrides it locally — getting this wrong has already applied a
  migration to production by accident.
- Building an index on a live table: use `CREATE INDEX CONCURRENTLY` inside
  `op.get_context().autocommit_block()`. A plain `CREATE INDEX` holds a write
  lock for the whole build.
- Data backfills belong in `scripts/`, not migrations — production skips
  migrations at boot, so a data migration there would silently never run.

---

## Database access from an agent

Read-only inspection of production is fine and often the fastest way to settle a
question. Writes need a script and a dry run.

```bash
URL=$(gcloud secrets versions access latest --secret=migration-database-url \
      --project=gen-lang-client-0452867537)
docker compose exec -T -e PROD_URL="$URL" backend python -c "
import os, re
from sqlalchemy import create_engine, text
url = re.sub(r'\+[a-z0-9]+://','://', os.environ['PROD_URL'])   # strip async driver
with create_engine(url).connect() as c:
    print(c.execute(text('select count(*) from stories')).scalar())
"
```

Two traps when inspecting schema:

- `story_tags` and `story_revisions` use **`stories_id`**, not `story_id`.
- `users.email` / `username` uniqueness is enforced by unique **indexes**, so
  `information_schema.table_constraints` won't show it. Check `pg_indexes`.

---

## Error handling

Errors are **RFC 7807 `application/problem+json`** via `app/error_handlers.py`.
Use `HTTPException` with a clear `detail`; the handler shapes the response.

Two specifics worth knowing:

- Validation errors must pass through `jsonable_encoder` — `RequestValidationError`
  can carry raw `bytes`, which `json.dumps` refuses. That turned a 422 into a 500.
- A 500 escapes *before* CORS headers are attached, so a backend crash shows up
  in the browser as a misleading CORS error. If you see CORS in the console,
  check the server logs before touching CORS config.

Race conditions are resolved by **database constraints, not read-then-write**:
catch `IntegrityError` and translate it (→ 409, or 401 for the token blacklist).
`StaleDataError` from the optimistic-lock column → 409.

---

## Tasks

`CELERY_TASK_ALWAYS_EAGER=true` in production: `.delay()` runs the task inline,
synchronously, in the web process. There is no worker and no broker consumer.

Consequences you must respect:

- **Always `commit()` before `.delay()`.** The inline task opens its own session
  and must see a committed row.
- **Celery's retry config is inert.** `autoretry_for`, `max_retries`,
  `retry_backoff` on a task do **nothing** in eager mode — `self.retry()` raises
  instead of re-running. Don't add a task that depends on retry semantics
  without revisiting ADR 001; and don't read an existing task's retry decorator
  as active protection.
- **A failed task fails silently.** `task_eager_propagates=False` means the
  exception never reaches the caller, which still returns 200. That is
  deliberate — a mail outage must not fail a signup — but it means the only
  evidence of a lost task is a log line. If a task must not be lost, retry
  *inside* it: `Mailer.send_email` does exactly this
  (`docs/adr/003-inline-smtp-retry.md`).
- Keep tasks fast — their latency is now user-visible request latency.

---

## Before you say you're done

```bash
docker compose exec --user root -T backend sh -c 'rm -rf /app/tests'
docker compose cp ./backend/tests backend:/app/tests
docker compose exec -T -e TEST_DB_BASE="postgresql://test_user:test_password@db:5432/quill_test" \
  -e NO_NETWORK=0 backend python -m pytest tests/ -m "not e2e" -q
```

The `rm -rf` + `cp` is required: only `backend/app` is bind-mounted, so edited
tests do not reach the container otherwise, and you will be running stale code.
Use `--user root` — the app user can't delete that directory.

Baseline: **394 passed**. Hot reload is not enabled; `docker compose restart
backend` after changing anything outside `app/`.
