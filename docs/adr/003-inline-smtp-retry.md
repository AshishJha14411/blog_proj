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

## A second problem the first version missed

Retrying inline fixed the silent loss but created a latency problem, raised by a
reader of the write-up:

> Eager mode is useful, but Cloud Run's request timeout is now the only bound
> your inline tasks have. A hung SMTP call that used to die at `task_time_limit`
> now sits on signup until the service timeout fires.

Correct, and worse than it sounds. `task_time_limit=30` is enforced *by a
worker*, so with no worker it is not enforced at all. `smtplib` has no default
socket timeout either — it inherits `None` and blocks until the OS gives up. The
only remaining bound was Cloud Run's **300s** request timeout (a platform
default, never chosen). A user could wait five minutes and receive a 504 on a
signup whose account row had already committed.

And a per-attempt timeout alone does not fix it: N attempts × a timeout, plus
backoff, is the real worst case. Three attempts at 10s is 33 seconds of
blocking — a worse promise than the single unbounded call it replaced, because
now it is *reliably* slow.

## Decision

Add a **bounded retry inside `Mailer.send_email`, governed by a hard total
deadline**:

| Setting | Default | Bounds |
|---|---|---|
| `SMTP_TIMEOUT_SECONDS` | 5s | one attempt (socket connect **and** commands) |
| `SMTP_TOTAL_BUDGET_SECONDS` | 12s | **every attempt plus all backoff** |

The budget is the real contract: the worst case a user waits on signup because
of email is **one number**, not a number times an attempt count. Attempts are
clipped to the remaining budget, and the loop stops when the budget runs out
rather than when `max_attempts` is reached.

Both are env vars so a misbehaving provider can be worked around without a
redeploy.

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

- **Signup latency grows on failure** — up to the budget (12s by default),
  because the send is inline. Success is unaffected (no sleep on the happy path,
  which is asserted by a test). Note signup sends **two** emails (verification +
  OTP), so a full mail outage costs up to two budgets.
- **The Cloud Run request timeout is still 300s** and still unset by the repo.
  It is no longer reachable via email, but it remains the only bound on any
  other slow dependency. Reported, deliberately not changed — it is shared with
  the AI streaming path, whose own `LLM_TIMEOUT` is 120s, so it cannot be
  lowered far.
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
