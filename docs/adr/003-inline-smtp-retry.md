# ADR 003 — Retry SMTP in-process, because Celery's retries don't run

**Status:** Accepted · **Date:** 2026-08-23 · **Deciders:** Ashish Kr Jha

## Context

[ADR 001](001-workerless-inline-tasks.md) removed the Celery worker and set
`task_always_eager=True`. It listed "no retries" as an accepted cost. In
practice that cost was larger and better hidden than the wording suggested.

`send_email_task` is configured for durability — `autoretry_for`, `max_retries=3`,
exponential backoff, jitter, and an idempotency claim released on failure so a
retry can re-acquire it. **None of it runs.** Eager mode does not retry:
`self.retry()` raises rather than re-executing. The task's own tests already
document this, asserting against `Retry` escaping `.apply()`.

Combined with `task_eager_propagates=False` (which exists so a mail failure
can't turn a successful signup into a 500), the real behaviour was:

> A single transient SMTP failure — a dropped connection, a momentary greylist —
> loses the signup verification email. The user gets HTTP 200, no error, no
> email, and nothing retries. They are stuck unless they think to hit resend,
> which they have no reason to do.

Two comments in the code actively asserted the opposite, claiming sends were
queued "asynchronously (over Redis) in prod" with "automatic retries". Anyone
reading `tasks/email.py` would reasonably conclude the path was protected.

The transient case is the common one, and it is recoverable in-process.

## Decision

Add a **small, bounded retry inside `Mailer.send_email`**: 3 attempts total with
a 1s linear backoff, so a failed send costs at most ~3 extra seconds.

Permanent failures short-circuit immediately via an explicit
`PERMANENT_SMTP_ERRORS` tuple — `SMTPAuthenticationError`,
`SMTPRecipientsRefused`, `SMTPSenderRefused`, `SMTPNotSupportedError`. Retrying
a rejected recipient or bad credentials is pure latency, and here that latency
is charged to a waiting user.

The dormant Celery retry config stays, with a comment marking it inert, because
it becomes correct the moment a worker exists.

## Why this is the right layer

- **It works with or without a worker.** The retry lives below the task, so it
  survives whatever the queue architecture becomes.
- **`smtplib.SMTPException` subclasses `OSError`**, so a blanket `except OSError`
  would have swallowed permanent failures into the retry loop. Naming them
  explicitly is what makes the loop safe.
- **The send is already idempotent at the task layer** (`claim_once` /
  `release`), so extra attempts cannot double-send.
- **Cost: zero.** No new service, no API to enable, no infrastructure.

## Consequences

**Accepted costs**

- **Signup latency grows on failure** — up to ~3s while attempts and backoff
  run, because the send is inline. Success is unaffected (no sleep on the happy
  path, which is asserted by a test).
- **It does not survive a sustained outage or a process restart.** Anything
  longer than a few seconds of SMTP unavailability still loses the email, still
  silently. This narrows the window; it does not close it.
- **Still no visibility.** A permanently lost email is logged and nothing else.
  There is no dead-letter queue and no operator alert.

**Gains**

- The common failure — a single transient blip — no longer loses a signup email.
- The code no longer claims protection it doesn't have.

## What the correct answer would be at scale

Unchanged from ADR 001: **Cloud Tasks push → an authenticated HTTP endpoint**.
That restores real durable retries with backoff while keeping scale-to-zero, and
at this volume it stays inside the free tier (1M operations/month) — the cost is
engineering time, not dollars.

The honest framing: this ADR buys most of the practical benefit for about an
hour of work and $0, and explicitly does not replace that migration.

**Revisit when:** email delivery becomes business-critical (payments, password
resets under load), a mail outage lasts long enough to matter, or someone needs
to answer "did this user ever receive their verification email?" — which today
nothing can answer.

## Alternatives considered

| Option | Cost | Why not (now) |
|---|---|---|
| Leave it | $0 | The bug. Silent data loss on the signup path. |
| **Bounded in-process retry** | $0 | **Chosen.** Recovers the common case; honest about its limits. |
| Cloud Tasks push | ~$0 at this volume | The right answer, deferred — re-architecture of the enqueue path. |
| Re-add the Celery worker | ~$5–15/mo | Reintroduces exactly the always-on instance ADR 001 deleted. |
| `task_eager_propagates=True` | $0 | Surfaces the failure — by turning a successful signup into a 500. Worse. |
| Retry from the frontend | $0 | The client can't see the failure; the response is already 200. |
