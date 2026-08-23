# Testing guide

**Baseline: backend 391 · frontend 89 · `tsc --noEmit` clean.** Treat anything
below that as a regression you introduced.

---

## The layers

| Layer | Location | Runs | Purpose |
|---|---|---|---|
| Backend unit | `backend/tests/unit/` | local + CI | Service logic against a real transactional DB |
| Backend integration | `backend/tests/integration/` | local + CI | Routes through the ASGI app, incl. WebSocket |
| Property / fuzz | `test_property_cursor.py`, `test_fuzz_endpoints.py` | local + CI | Hypothesis-generated inputs |
| Frontend unit | `frontend/tests/unit/` | local + CI | Hooks, services, pure logic |
| Component integration | `frontend/tests/component-integration/` | local + CI | Components with providers, via Testing Library |
| E2E | `frontend/tests/e2e/*.cy.ts` | **CI only** | Full journeys in a browser |

Backend markers (`pytest.ini`): `unit`, `integration`, `e2e`. Local runs use
`-m "not e2e"`.

---

## Running them

### Backend

```bash
docker compose exec --user root -T backend sh -c 'rm -rf /app/tests'
docker compose cp ./backend/tests backend:/app/tests
docker compose exec -T -e TEST_DB_BASE="postgresql://test_user:test_password@db:5432/quill_test" \
  -e NO_NETWORK=0 backend python -m pytest tests/ -m "not e2e" -q
```

**The copy step is mandatory.** Only `backend/app` is bind-mounted, so edited
tests never reach the container by themselves — skip it and you are testing a
stale copy while believing you aren't. `--user root` is required because the app
user cannot delete `/app/tests`.

Narrower runs:

```bash
… backend python -m pytest tests/unit/services/test_story_service.py -q
… backend python -m pytest tests/ -m "not e2e" -q -k "popular or tags"
```

### Frontend

```bash
docker compose exec -T frontend npx vitest run
docker compose exec -T frontend npx vitest run tests/unit/hooks/useUnreadNotifications.test.ts
docker compose exec -T frontend npx vitest run -t "part of the test name"
docker compose exec -T frontend npx tsc --noEmit
```

`--reporter=basic` is **not** a valid reporter in this Vitest version and fails
at startup. The default reporter is fine; strip ANSI if you need to grep:

```bash
docker compose exec -T frontend npx vitest run 2>&1 | sed 's/\x1b\[[0-9;]*m//g' | grep -E "Tests |FAIL"
```

### E2E — CI only, and why

Cypress **cannot run locally in this environment**:

- host `node`/`npx` abort with `Illegal instruction`;
- inside the container the specs' hardcoded `localhost:8000` doesn't resolve to
  the backend (it is `backend:8080` on the compose network).

So CI is the only place e2e executes. The practical consequence is a real trap:

> **Changing user-visible copy passes every local check and fails in CI.**
> Cypress asserts on rendered strings. After any rename:
> ```bash
> grep -rn "<old string>" frontend/tests/
> ```

This has already broken a build — a rename updated the app and the vitest specs
but not `story.cy.ts`.

Specs: `auth.cy.ts`, `negative.cy.ts`, `reader.cy.ts`, `story.cy.ts`. They live
in `frontend/tests/e2e/`, **not** in a `cypress/` directory.

---

## Backend patterns

### Session and isolation

`tests/conftest.py` gives each test a `db_session` inside a transaction that is
rolled back afterwards, so tests don't leak into each other. Use the factories
in `tests/factories.py` (`UserFactory`, `RoleFactory`, `StoryFactory`, …) rather
than hand-building rows.

### Testing async service functions

Production reads are `async`, but the test session is sync. `conftest.py`
provides `_AsyncSessionAdapter` to bridge them, and each test module defines
thin wrappers:

```python
import asyncio as _asyncio
from tests.conftest import _AsyncSessionAdapter

def _run_async(coro):
    loop = _asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

def _get_popular_stories(db_session, *a, **k):
    return _run_async(story_service.get_popular_stories(_AsyncSessionAdapter(db_session), *a, **k))
```

Add a wrapper alongside the existing ones when you add an async service function.

### Things the DB enforces

`likes` and `bookmarks` carry `UNIQUE (user_id, story_id)`. A test that needs
several likes on one story needs **several users** — the same user twice raises
`IntegrityError`. Same shape for `oauth_accounts (provider, subject)`.

### Tasks

`moderate_story_task` is stubbed globally in `conftest.py` so it doesn't open a
second session outside the test transaction. If your code path depends on
moderation having run, set the resulting state directly and say why in a
comment; task behaviour itself is covered in `tests/unit/tasks/`.

---

## Frontend patterns

### Queries need a provider — and the right one

Anything using TanStack Query needs a `QueryClientProvider`. **A test client
built without `staleTime` behaves differently from production**, which sets
`staleTime: 30_000` in `app/providers.tsx`:

```typescript
// Typical: fine for most tests
new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })

// For cache-sensitive behaviour, mirror production or you will not catch the bug
new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0, staleTime: 30_000 } } })
```

The unread-badge bug passed four existing tests because they all used the first
form, which refetches where production doesn't. The regression test uses the
second and starts from the signed-out state to reproduce the real token timing.

### Auth in tests

```typescript
useAuthStore.getState().login({
  accessToken: 'test-access-token',
  refreshToken: 'test-refresh-token',
  user: { id: 'u1', username: 'tester', email: 'tester@example.com' },
});
// and logout() in afterEach — the store is module-level and leaks between tests
```

Remember `accessToken` is memory-only, so a test that starts "signed in" is not
reproducing a fresh page load. If the behaviour depends on that gap, start
signed out and sign in mid-test.

---

## Writing a regression test

**A regression test that passes on the broken code proves nothing.** The
required loop:

1. Write the test.
2. **Revert the fix** (or stash it) and run the test — confirm it *fails*, and
   note the failure message.
3. Restore the fix and confirm it passes.
4. Put the reproduction in a comment, including the real-world symptom.

Example from `useUnreadNotifications.test.ts`: with `initialData: 0` restored,
the test failed `expected +0 to be 2` — exactly the production symptom (badge
showed 0 while the API returned 2). That message is recorded in the test's
comment so a future reader knows what it protects.

---

## What to test

Test: business rules, permission boundaries, error translation
(`IntegrityError` → 409), pagination/cursor edges, cache invalidation, and every
bug you fix.

Don't test: framework behaviour, generated types, or exact markup — markup churns
with every redesign and the assertion adds no signal.

---

## CI

`.github/workflows/ci.yml` — gitleaks, backend tests (real Postgres + Redis),
frontend tests, Trivy (non-blocking), then Cypress gated on the first two.
Artifacts (videos, screenshots) upload on e2e failure and are the fastest way to
see what the browser actually rendered.
