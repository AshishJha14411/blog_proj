# frontend/CLAUDE.md — rules for frontend work

Scoped rules for `frontend/`. Read `../CLAUDE.md` first for project-wide rules.

This file documents **contracts and patterns**, not current markup. The visual
layer changes often; the rules below are what must survive a redesign.

---

## Stack

Next.js 15 (App Router, Turbopack) · React 19 · TypeScript · Tailwind v4 ·
TanStack Query v5 · zustand · axios · Vitest + Testing Library · Cypress.

---

## The three-layer rule

```
app/          Routes. Server Components by default; "use client" only when
              you need state, effects, or browser APIs.
components/   ui/     — primitives (Button, Input, Card, …)
              common/ — app composites (PostCard, Navbar, forms)
              <feature>/ — ads, auth, story, support
services/     EVERY network call. No component imports axios directly.
hooks/        Shared client logic. stores/ — zustand. lib/ — axios, types, errors.
```

**A component must never call `axios` directly.** Add or reuse a function in
`services/`. This keeps the API surface greppable, and it is what made a
backend-contract mismatch findable in one search.

---

## Data: server state vs client state

| Kind | Tool | Notes |
|---|---|---|
| Server data | **TanStack Query** | `app/providers.tsx` sets `staleTime: 30_000` |
| Auth | **zustand** (`stores/authStore.ts`) | persisted to `localStorage` |
| UI/ephemeral | `useState` | |

### `staleTime: 30_000` changes how you must write queries

**Never use `initialData` on a query that starts disabled.** `initialData` is
written to the cache stamped `dataUpdatedAt = now`, so with a 30s `staleTime` it
counts as *fresh* and no fetch is issued. Combined with an `enabled` gate that
opens a moment later, the seeded placeholder can persist indefinitely.

This is not hypothetical: the notification badge showed `0` in production for
weeks while the API returned `{"count": 2}`. Use `data ?? fallback` at the render
site instead of seeding the cache.

Note that a `QueryClient` built in a test **without** `staleTime` refetches where
production does not — so a test can pass while production is broken. Tests for
cache-sensitive behaviour must mirror `app/providers.tsx`. See
`tests/unit/hooks/useUnreadNotifications.test.ts` for the pattern.

### Auth token model

`accessToken` is **memory-only** — deliberately excluded from `partialize` so an
XSS payload can't read it out of `localStorage`. `refreshToken`, `user` and
`isAuthenticated` are persisted.

Consequences:

- On every page load and in every new tab, `accessToken` is `null` until
  `AuthInitializer` mints one from the refresh token. **Any `enabled: !!accessToken`
  gate is false on first render.**
- Use `useHydratedAuth()` rather than reading the store directly when render
  depends on auth — it waits for zustand rehydration and avoids a flash of
  signed-out UI.
- The axios instance already does **401 → refresh → retry**. Don't rebuild that
  in a component.

### Mutations must invalidate, not hand-patch

After a mutation, invalidate the query key. Do not keep a parallel local counter
alongside server state — the bell did (`socketUnread + polled`) and double-counted
every notification once the server figure caught up. One source of truth: the
server.

---

## Types are generated — never hand-edit `lib/api-types.ts`

`postService.Post` aliases the generated `StoryOut`. A backend contract change
becomes a **compile error**, which is the whole point.

Regenerate after any backend schema change (the npm script's URL doesn't resolve
from inside the container, so use the file form):

```bash
curl -s http://localhost:8000/openapi.json -o /tmp/openapi.json
docker compose cp /tmp/openapi.json frontend:/tmp/openapi.json
docker compose exec -T frontend npx openapi-typescript /tmp/openapi.json -o lib/api-types.ts
docker compose exec -T frontend npx tsc --noEmit
```

---

## API access rules

- The axios instance's `baseURL` is `${API_URL}/api/v1`, so service calls use
  paths **relative to the version prefix** (`/stories/`, not `/api/v1/stories/`).
- **WebSocket routes are top-level**, not under `/api/v1`. They must be called
  with an absolute URL built from `API_URL`. A relative call silently 404s — this
  killed support chat once.
- **Some paths need their trailing slash.** `/me/notifications/` without it
  307-redirects, and browsers strip `Authorization` on cross-origin redirects, so
  the retried request 401s. If an authed call 401s for no clear reason, check the
  slash.
- Server Components cannot reach `NEXT_PUBLIC_API_URL` in Docker — they run in
  the frontend's own Node process, where `localhost:8000` is the *frontend*
  container. `lib/axios.ts` branches on `typeof window` and uses
  `API_URL_INTERNAL` server-side. Don't "simplify" that branch away.

---

## Styling

Tailwind v4, **CSS-first**: there is no `tailwind.config.js`. Design tokens are
declared in an `@theme` block in `app/globals.css` — that file is the source of
truth, so read it before assuming a class exists.

**Only names declared in `@theme` generate utilities.** A class like
`bg-something-alt` whose token was never declared silently produces *no style* —
Tailwind emits nothing and the element renders unstyled, with no error and no
warning. This has shipped here before. When adding a colour: declare the token
in `@theme` first, then use it. When a surface looks unexpectedly transparent,
check the token exists before debugging anything else.

Use the **semantic** tokens (`bg-surface`, `text-text-subtle`,
`border-border-soft`), not raw hex or arbitrary values. Dark mode works by
reassigning the underlying variables in one `.dark` block, so anything built on
a token follows automatically — and anything built on a literal colour doesn't.

**Dark mode is class-based and provider-free.** The `dark` class on `<html>` is
the source of truth; an inline script in `app/layout.tsx` applies it before
first paint, and `ThemeToggle` flips it. That script must remain the **first
child of `<body>`** — never a hand-written `<head>` (see `docs/GOTCHAS.md`).

Full explanation: [`README.md` → Design system and theming](README.md#design-system-and-theming).

---

## Testing

```bash
docker compose exec -T frontend npx vitest run     # baseline: 89 passing
docker compose exec -T frontend npx tsc --noEmit   # must be clean
```

**Cypress does not run locally in this environment** — host `node` dies with
`Illegal instruction`, and in-container the specs' hardcoded `localhost:8000`
doesn't resolve. CI is the only place e2e actually executes.

Therefore: **user-facing copy is load-bearing.** Cypress asserts on visible
strings, and it is excluded from local runs, so a rename passes everything
locally and fails in CI. After changing any visible text:

```bash
grep -rn "<the old string>" frontend/tests/
```

Details and patterns in `docs/TESTING.md`.

---

## Environment

| Var | Scope | Purpose |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | browser | API origin from the user's browser |
| `API_URL_INTERNAL` | server only | API origin from inside the container — `http://backend:8080`. **Port 8080, not 8000**: the container listens on 8080 and compose publishes it to the host as 8000 |
| `NEXT_PUBLIC_SITE_URL` | browser | canonical site URL (OpenGraph, sitemap) |

Deliberately **not** `NEXT_PUBLIC_`-prefixed: `API_URL_INTERNAL` is server-only.

---

## Deployment

**Vercel builds `main`.** Pushing to `dev` deploys nothing — frontend changes go
live only when the PR merges. Say so when reporting, otherwise "it's fixed" reads
as "it's live" and it isn't.

---

## Known environment quirk

Turbopack racing the Windows bind mount produces 500s with
`ENOENT … _buildManifest.js.tmp`. It is not your code:

```bash
docker compose restart frontend
```
