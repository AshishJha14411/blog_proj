# CLAUDE.md — working agreement for AI agents

Read this before changing anything. It is the orientation layer: where things
live, what the rules are, and which mistakes have already been made here so you
don't repeat them.

Claude Code loads this file automatically. `backend/CLAUDE.md` and
`frontend/CLAUDE.md` add scoped rules for those trees.

---

## What this project is

**Quill & Code** — a full-stack AI-assisted blogging platform.
FastAPI + PostgreSQL backend, Next.js 15 (App Router) frontend, deployed on
Cloud Run + Vercel + Neon + Upstash. It is a portfolio piece: code quality and
the *reasoning behind decisions* matter as much as shipped features.

That last point shapes how you write code here. See **Comments** below.

---

## Ground rules

1. **Verify, don't assume.** This codebase has had bugs that looked like one
   thing and were another — an empty analytics page that was a 404, a "no data"
   badge that was a cache artifact. Before you diagnose, get evidence: query the
   database, call the endpoint, read the rendered output.
2. **Never invent an endpoint, column, or config key.** Grep for it. If the
   frontend calls something the backend doesn't serve, that is a bug to report,
   not a contract to honour. (This exact drift shipped once — see
   `docs/GOTCHAS.md`.)
3. **Tests are the contract.** `backend/tests` and `frontend/tests` must pass
   before you claim done. Current baseline: **backend 385, frontend 89, `tsc`
   clean.** If you change user-facing copy, grep `frontend/tests/e2e/` too — it
   does *not* run locally, so CI is the first place it fails.
4. **Don't commit or push unless asked.** The owner reviews before commits, and
   prefers few, well-described commits over many small ones.
5. **Don't deploy unless asked.** See `docs/DEPLOY.md` for the sequence, which
   is canary-first for a reason.
6. **Secrets never enter the repo**, not even in an example. CI runs gitleaks.

---

## Where things live

```
blog_proj/
├── CLAUDE.md              ← you are here
├── README.md              # project showcase: architecture, features, design
├── backend/
│   ├── CLAUDE.md          # backend rules — READ before backend work
│   ├── README.md          # API tables, DB schema with columns, migrations
│   ├── app/
│   │   ├── main.py        # app factory, middleware order, router mounts
│   │   ├── routes/        # HTTP layer — thin; no business logic
│   │   ├── services/      # business logic + transaction boundaries
│   │   ├── models/        # SQLAlchemy ORM
│   │   ├── schemas/       # Pydantic contracts = the OpenAPI source of truth
│   │   ├── authz/         # Perm enum + ROLE_PERMS matrix
│   │   ├── tasks/         # Celery tasks (run inline in prod — see ADR 001)
│   │   ├── ws/ + support/ # WebSocket routers (mounted at top level, NOT /api/v1)
│   │   ├── middleware/, core/, llm/, utils/
│   │   └── seed.py        # deterministic seed data (used by CI e2e)
│   ├── scripts/           # one-off operational scripts (see below)
│   ├── alembic/versions/  # linear migration chain
│   └── tests/             # unit · integration · property/fuzz
├── frontend/
│   ├── CLAUDE.md          # frontend rules — READ before UI work
│   ├── README.md
│   ├── app/               # App Router routes
│   ├── components/        # ui/ primitives · common/ composites · feature dirs
│   ├── services/          # ALL network calls live here
│   ├── hooks/ · stores/ · lib/
│   └── tests/             # unit · component-integration · e2e (Cypress)
└── docs/
    ├── DEVELOPMENT.md     # setup, daily workflow, exact commands
    ├── TESTING.md         # test architecture + how to add tests
    ├── GOTCHAS.md         # traps that have already cost real debugging time
    ├── DEPLOY.md          # production runbook
    ├── performance.md     # the latency investigation, before/after
    ├── adr/               # architecture decision records + index
    ├── architecture/      # animated diagram + the script that generates it
    └── screenshots/
```

---

## Start here, by task

| Task | Read first |
|---|---|
| Anything backend | `backend/CLAUDE.md`, then `backend/README.md` |
| Anything frontend/UI | `frontend/CLAUDE.md` |
| Adding an endpoint | `backend/CLAUDE.md` § Adding an endpoint |
| Changing the database | `backend/CLAUDE.md` § Migrations |
| Writing/fixing tests | `docs/TESTING.md` |
| "Why is this broken?" | `docs/GOTCHAS.md` — check here before debugging |
| Deploying | `docs/DEPLOY.md` |
| A significant design decision | `docs/adr/README.md` — write an ADR |

---

## Commands (all run through Docker)

```bash
docker compose up -d                 # frontend :3000, backend :8000, db, redis

# Backend tests — note the tests/ copy step; only app/ is bind-mounted
docker compose exec --user root -T backend sh -c 'rm -rf /app/tests'
docker compose cp ./backend/tests backend:/app/tests
docker compose exec -T -e TEST_DB_BASE="postgresql://test_user:test_password@db:5432/quill_test" \
  -e NO_NETWORK=0 backend python -m pytest tests/ -m "not e2e" -q

# Frontend
docker compose exec -T frontend npx vitest run
docker compose exec -T frontend npx tsc --noEmit
```

Full explanations in `docs/DEVELOPMENT.md`. **Cypress cannot run locally here**
— see `docs/TESTING.md`.

---

## Architecture in one screen

- **Routes are thin.** They validate, call a service, serialise. Business logic
  and transaction boundaries live in `app/services/`.
- **Reads are async, writes are sync.** Deliberate: writes must keep the
  `commit → refresh → enqueue` ordering. Async has no lazy IO, so **every**
  relationship an async read touches must be eager-loaded (`joinedload` /
  `selectinload`) or you get `MissingGreenlet`.
- **Authorization is a permission matrix**, not role string checks. Use
  `has_perm(user, Perm.X)` / `require(Perm.X)` from `app/authz`.
- **The API is versioned at `/api/v1`.** WebSocket routes are top-level and are
  *not* under the prefix. A legacy unversioned mount still exists for a
  deprecation window; use the versioned paths.
- **Types flow one way**: SQLAlchemy models → Pydantic schemas → OpenAPI →
  `frontend/lib/api-types.ts`. Frontend types are **generated**; never hand-edit
  them. Backend contract changes surface as frontend compile errors, which is
  the point.
- **No Celery worker in production** — tasks run inline
  (`CELERY_TASK_ALWAYS_EAGER`). This is a deliberate cost trade-off with real
  consequences (no retries). Read `docs/adr/001-workerless-inline-tasks.md`
  before touching anything task-related.

---

## Comments: explain *why*, never *what*

This codebase uses a `/** WHY: ... **/` convention for decisions whose reasoning
isn't recoverable from the code. Keep it. A comment earns its place if removing
it would let someone "simplify" the code back into a bug.

```python
# /** WHY: `_excerpt_for_list` must use set_committed_value, not assignment.
#     `content` is a mapped column — a plain assignment marks the instance
#     dirty and the unit-of-work commits the truncated body back over the
#     real story. A read request would silently destroy data. **/
```

Do **not** write `# increment counter` above `counter += 1`. Match the density
of the surrounding file.

---

## Operational scripts

`backend/scripts/` holds reviewed, idempotent operational actions instead of
ad-hoc SQL typed at production:

- `backfill_story_tags.py` — derive tags from genre for pre-existing stories
- `grant_superadmin.py` — promote or seed an operator account

Both take `--dry-run` and read `DATABASE_URL`. **Always dry-run against
production first.** If you need a new one-off production action, add a script
here rather than running raw SQL — it makes the action reviewable and repeatable.

---

## Definition of done

1. Backend tests pass (385+), frontend tests pass (89+), `tsc --noEmit` clean.
2. New behaviour has a test. A bug fix has a **regression test that you verified
   fails without the fix** — this is not optional; a test that passes on the
   broken code proves nothing.
3. Copy changes: grep `frontend/tests/e2e/` for the old string.
4. Docs updated when behaviour changed (`README.md` API tables,
   `docs/GOTCHAS.md` if you found a new trap, an ADR if the decision was
   structural).
5. Report honestly: what you verified vs. what you assumed. If something is
   unverified, say so.
