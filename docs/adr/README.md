# Architecture Decision Records

An ADR captures a decision that is **hard to reverse or easy to "fix" back into
a bug** — the reasoning that isn't recoverable from reading the code.

## Index

| # | Decision | Status | Date |
|---|---|---|---|
| [001](001-workerless-inline-tasks.md) | Run background tasks inline; drop the always-on Celery worker | Accepted | 2026-07-27 |
| [002](002-genre-as-tags.md) | Story genre becomes its tags, with no controlled vocabulary | Accepted | 2026-08-06 |
| [003](003-inline-smtp-retry.md) | Retry SMTP in-process, because Celery's retries don't run | Accepted | 2026-08-23 |

## When to write one

Write an ADR when:

- the decision constrains future work (a framework, a data model, a boundary);
- you chose a **worse-on-paper** option for a real reason (cost, time, risk) —
  this is the most valuable kind, because otherwise someone "corrects" it later;
- you rejected the obvious approach and the rejection isn't self-evident;
- reversing it would mean a migration or a broad refactor.

Don't write one for a bug fix, a refactor with no trade-off, or something the
code already says plainly. Those belong in a `/** WHY: **/` comment or
`GOTCHAS.md`.

## How

Copy the template below to `NNN-short-kebab-title.md`, add a row to the index.
ADRs are **immutable once accepted** — if a decision changes, write a new ADR
that supersedes it and update the old one's status to `Superseded by NNN`.
Rewriting history hides the reasoning, which is the whole point of the record.

## Template

```markdown
# ADR NNN — <decision, stated as an action>

**Status:** Proposed | Accepted | Superseded by NNN · **Date:** YYYY-MM-DD · **Deciders:** <names>

## Context

The forces at play: the constraint, the measurement, the thing that broke.
Facts and numbers, not opinions. Someone should be able to disagree with the
decision while agreeing with this section.

## Decision

What was chosen, stated plainly and actively.

## Why this is safe here specifically

What is true about *this* codebase that makes the choice work. This is the
section that stops a future reader from generalising the decision somewhere it
doesn't hold.

## Consequences

**Accepted costs** — what is genuinely worse now. Be honest; a cost-free
decision needs no ADR.

**Gains** — what improved.

## What the correct answer would be at scale

If this is a deliberate trade-off rather than a best practice, say what the
right answer is and why it wasn't chosen now. This is what turns a compromise
into demonstrated judgement.

**Revisit when:** the specific conditions that would flip the decision.

## Alternatives considered

| Option | Cost | Why not (now) |
|---|---|---|
```
