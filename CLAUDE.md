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
   before you claim done. Current baseline: **backend 394, frontend 89, `tsc`
   clean.** If you change user-facing copy, grep `frontend/tests/e2e/` too — it
   does *not* run locally, so CI is the first place it fails.
4. **Update the docs in the same change, always.** Documentation is part of the
   work, not a follow-up task — a doc that lags is worse than no doc, because it
   is trusted. This is not optional and it is not "if time permits". See
   **Keeping docs true** below for exactly which file to touch.
5. **Don't commit or push unless asked.** The owner reviews before commits, and
   prefers few, well-described commits over many small ones.
6. **Don't deploy unless asked.** See `docs/DEPLOY.md` for the sequence, which
   is canary-first for a reason.
7. **Secrets never enter the repo**, not even in an example. CI runs gitleaks.

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
- **No Celery worker anywhere** — tasks run inline (`CELERY_TASK_ALWAYS_EAGER`),
  in production *and* by default locally, so the two behave the same. A
  deliberate cost trade-off with real consequences: **Celery's own retry config
  is inert**, and a failed task fails silently. Where a task must not be lost,
  the retry lives inside the operation (`Mailer.send_email`). Read
  `docs/adr/001-workerless-inline-tasks.md` and `docs/adr/003-inline-smtp-retry.md`
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
- `delete_users.py` — remove accounts, optionally reassigning authored stories
  so deleting a test account can't quietly destroy published content
  (`--reassign-to`). Discovers the ~19 tables referencing `users.id` from the
  catalog rather than a hardcoded list, and handles each by meaning: authored
  content reassigned, nullable references nulled, account data deleted.

Both take `--dry-run` and read `DATABASE_URL`. **Always dry-run against
production first.** If you need a new one-off production action, add a script
here rather than running raw SQL — it makes the action reviewable and repeatable.

---

## Keeping docs true

**Every change updates its docs in the same commit.** Not afterwards, not "when
there's time". Stale documentation is actively harmful here because these files
are what the next agent reads *instead of* the code — a wrong line propagates
into decisions. This project has already shipped comments asserting that emails
were queued with automatic retries when they were neither.

Find your change in the left column and update the right one. If a row applies
and you skipped it, the task is not done.

| You changed… | Update |
|---|---|
| An endpoint, its params or its response | `backend/README.md` API table + regenerate `frontend/lib/api-types.ts` |
| The database schema | `backend/README.md` — the ERD **and** the table list |
| A command, flag, port or env var | `docs/DEVELOPMENT.md` (and `.env.example` if it's config) |
| Behaviour a test locks in | the test, plus `docs/TESTING.md` if the *pattern* is new |
| Anything user-visible | grep `frontend/tests/e2e/` — Cypress asserts on copy and only runs in CI |
| A decision that constrains future work | a new ADR + a row in `docs/adr/README.md` |
| A trap that cost you debugging time | `docs/GOTCHAS.md`, symptom-first |
| The deploy sequence or a prod setting | `docs/DEPLOY.md` |
| The test count | the baseline in `CLAUDE.md`, `docs/TESTING.md`, `docs/DEVELOPMENT.md`, `README.md`, `backend/README.md` |
| Conventions or a guardrail | the relevant `CLAUDE.md` (root / `backend/` / `frontend/`) |

**Also: correct what your change makes false.** Updating your own new docs isn't
enough — grep for claims elsewhere that your change just invalidated, including
`/** WHY **/` comments in code. When ADR 003 added retries, the flat claim "no
retries" was left standing in four separate files, all of which had been true
the day before.

ADRs are the exception: they are immutable once accepted. Supersede with a new
one, or add a dated note; never rewrite the record.

**Verify, don't assert.** If you document a command, run it. If you document a
number, measure it. If you can't verify something, say so in the text rather
than stating it as fact.

## Definition of done

1. Backend tests pass (394+), frontend tests pass (89+), `tsc --noEmit` clean.
2. New behaviour has a test. A bug fix has a **regression test that you verified
   fails without the fix** — this is not optional; a test that passes on the
   broken code proves nothing.
3. Copy changes: grep `frontend/tests/e2e/` for the old string.
4. **Docs updated in this same change** — walk the table in **Keeping docs
   true** and confirm every applicable row, including correcting statements
   elsewhere that your change made false. A change is not done while a doc
   contradicts it.
5. Report honestly: what you verified vs. what you assumed. If something is
   unverified, say so.
