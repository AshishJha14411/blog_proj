# ADR 001 — Run background tasks inline; drop the always-on Celery worker

**Status:** Accepted · **Date:** 2026-07-27 · **Deciders:** Ashish Kr Jha

## Context

The app enqueues background work through Celery over Redis: story moderation,
transactional email, webhook delivery, support tickets. In production the
consumer ran as a second Cloud Run service (`quill-worker`).

A Celery worker is a **polling** consumer — it has no HTTP surface, it sits in a
`BRPOP` loop against the broker. Cloud Run only allocates CPU in response to
requests, and only scales up on requests. A polling worker therefore requires:

```
--min-instances=1 --max-instances=1 --no-cpu-throttling
```

which means **one CPU billed 24/7**, whether or not any task ever runs. Two
costs follow:

1. **Cloud Run:** a continuously-billed instance — the largest line item in the
   stack, since every other component scales to zero. Order of magnitude:
   single-digit to low-teens USD/month.
2. **Upstash:** kombu polls the broker roughly once per second, forever —
   ~86k+ commands/day produced by an idle system, consuming free-tier quota.

The service is idle the overwhelming majority of the day, and operates under a
hard cost ceiling. A continuously-billed instance to serve a queue that is empty
almost all the time is not justifiable.

## Decision

Set `CELERY_TASK_ALWAYS_EAGER=true` in production and **delete the worker
service**. `.delay()` then executes the task **inline, synchronously, in the
calling web process**. No worker, no broker traffic, no idle spend.

Also set `task_eager_propagates=False`, so a failing task cannot raise into the
HTTP request and turn a successful write into a 500.

## Why this is safe in this codebase specifically

- **Enqueue happens after commit.** Every `.delay()` call site commits first
  (`db.commit()` → `db.refresh()` → `.delay()`), so the inline task opens its own
  session and sees a committed row. Had the order been reversed, inline
  execution would have raced an invisible row and silently failed.
- **Tasks are already idempotent** (built for at-least-once delivery with
  `task_acks_late`), so inline re-execution is harmless.
- **The latency is genuinely small.** `moderate_content` is a local
  `better_profanity` scan — no LLM call, no network. Inline moderation costs
  milliseconds. The only task with real latency is SMTP on signup (~1–2s).
- **Work happens *during* the request**, so Cloud Run has CPU allocated. This is
  why inline works where `FastAPI BackgroundTasks` would not: post-response work
  on a scale-to-zero service is CPU-throttled to near-zero and dies silently.

## Consequences

**Accepted costs**
- **No retries or backoff.** Eager mode does not retry. A transient SMTP failure
  loses that email; the user must trigger a resend. This is the real price.
  *(Update 2026-08-23 — this cost proved sharper than written. The loss is also
  **silent**: `task_eager_propagates=False` hides the failure, so signup returns
  200 and the user is never told. The common transient case is now handled by a
  bounded in-process retry inside `Mailer` — see
  [ADR 003](003-inline-smtp-retry.md). The decision recorded here is unchanged:
  still no worker, still no durable retries.)*
- **No time limits.** `task_time_limit` is ignored in eager mode, so a task can
  only be bounded by the caller's own timeouts.
- **Task latency is now user-visible** — signup carries the SMTP round-trip.
- **No task-level parallelism**; work competes with request handling.

**Gains**
- Idle infrastructure cost → **$0**. Broker polling → **0 commands/day**.
- One less service to deploy, secure, and monitor.
- Redis is still used (rate limiting, cache, WS pub/sub), so nothing else changes.

## What the correct answer would be at scale

**Push delivery, not pull.** Replace the polling broker with **Cloud Tasks** (or
Pub/Sub push) targeting an authenticated HTTP endpoint on the existing backend
service:

```
create story ──► Cloud Tasks enqueue ──► POST /internal/tasks/moderate
                                          └─► Cloud Run cold-starts 0→1, works, scales back
```

That keeps **scale-to-zero *and* asynchronous execution *and* managed retries
with backoff** — it is strictly better than both the always-on worker and the
inline approach, and Cloud Tasks' free tier (1M operations/month) would make it
free at this volume too. It was not chosen now only because it is a
re-architecture of the enqueue path, and the inline switch is a one-line config
change that solves the immediate cost problem today.

**Revisit this ADR when:** task volume grows, retries start mattering
(e.g. real transactional email), a task exceeds ~1s of user-visible latency, or
the project is funded by something other than a personal wallet.

## Alternatives considered

| Option | Cost | Why not (now) |
|---|---|---|
| Keep the always-on worker | ~$5–15/mo | The problem being solved. |
| `min-instances=0` on the worker | $0 | **Broken, not cheap** — nothing wakes a polling consumer, so the queue silently never drains. |
| Cloud Scheduler → Cloud Run Job draining the queue | ~$0 | Works, but keeps Celery + broker polling and adds up to N minutes of latency, for more moving parts than inline. |
| e2-micro Always Free VM running the worker | ~$0 | Genuinely viable fallback. Rejected because it reintroduces a server to patch and manage, and external egress to Upstash/Neon is not free-tier-unlimited. |
| **Cloud Tasks push → HTTP endpoint** | ~$0 | **The right answer** — deferred as a re-architecture, not rejected. See above. |
