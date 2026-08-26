# ADR 004 — Automated moderation holds for review; it never rejects

**Status:** Accepted · **Date:** 2026-08-26 · **Deciders:** Ashish Kr Jha

## Context

Every story published on the platform is scanned by `moderate_content`, a
keyword profanity check. Two properties of the original design combined badly.

**It flagged on the first hit**, and **a flag meant `rejected`** — the row was
unpublished, its status set to `rejected`, and the author notified that their
story had been rejected. No human was involved.

Because profanity is matched per word, the probability of at least one hit
rises with word count. So the rule "flag if any profane word appears" is, in
practice, a filter on length. Measured against the ten real stories in
production:

| Story | Words | Profane words | Old rule | New rule |
|---|---|---|---|---|
| The Grim Dawn | 4,432 | 3 | **REJECTED** | ok |
| The starry Night | 3,964 | 5 | **REJECTED** | ok |
| The House That Waited | 3,928 | 1 | **REJECTED** | ok |
| Coffee, Silence, and Strangers | 3,391 | 3 | **REJECTED** | ok |
| A dark window through the jungle | 2,928 | 0 | ok | ok |
| The darkness of the soul | 1,966 | 1 | **REJECTED** | ok |
| Borrowed Lives | 1,298 | 2 | **REJECTED** | ok |
| What the Eyes Refuse to Hide | 573 | 1 | **REJECTED** | ok |
| The Crimson Vow | 269 | 0 | ok | ok |
| The Last Table by the Window | 78 | 1 | **REJECTED** | ok |

**Seven of ten** ordinary stories were auto-rejected. Every story over 1,000
words was. The highest profanity count in any real story was **5** — this was
firing on fiction, not on abuse. On a creative-writing platform that is a
product defect, and it destroyed the author's work by default.

A previous attempt addressed this by whitelisting mild words (`hell`, `damn`,
`ass`, `bastard`). It helped and was not enough: it is a guess about which
words fiction is permitted to contain, and it still auto-rejected when the
guess was wrong.

## Decision

**Two changes, addressing different halves of the problem.**

**1. A flag holds the story for review. It never rejects.**
Flagged stories stay `pending` with `is_flagged=True`, unpublished, with an
open `Flag` for the moderation queue. The author is notified `story_held_for_review`.
Only a human sets `rejected`.

**2. Flag on saturation, not presence.**
`MODERATION_PROFANITY_THRESHOLD` (default **10** occurrences) replaces the
first-hit trigger. Occurrences, not distinct words — one word used twenty times
is a stronger signal than twenty used once. Env-tunable, because the right
number is an operational judgement.

These are independent and both are needed. The threshold cuts false positives;
holding for review makes the remaining false positives *recoverable* instead of
destructive.

## What is deliberately preserved

**Flagged content is still never auto-published.** That is the safety property,
and it is untouched — the story is unlisted, flagged, and queued. The change is
only to what happens to work that automation is unsure about: it waits for a
person instead of being thrown away.

## Consequences

**Accepted costs**

- **Moderators now have a real queue.** Previously the automation "decided" and
  the queue was mostly empty. Held stories need someone to look at them; if
  nobody does, an author waits indefinitely. There is no SLA and no reminder.
- **A single slur in an otherwise clean story no longer flags.** The threshold
  is a false-positive fix, not a safety upgrade. If zero tolerance is ever
  needed for specific terms, add a **separate** severe-terms list that flags at
  count ≥ 1 — do *not* lower this threshold, which reintroduces the length bias.
- **Counting costs more than a boolean check** — measured 364 ms for a
  4,400-word story, inline in the publish request. Acceptable at this size;
  revisit if stories get much longer.

**Gains**

- Long-form writing is publishable. The platform's main use case works.
- No author loses work to a keyword match.
- The moderation queue shows what it claims to show.

## Alternatives considered

| Option | Why not |
|---|---|
| Extend the whitelist further | Endless guessing about which words fiction may contain; still auto-rejects when wrong. |
| Scale the threshold by length (a density ratio) | Tempting, but it lets a 20,000-word story carry proportionally more abuse. Saturation as an absolute count is the safer shape. |
| Send flagged stories to `rejected` but allow appeal | Same destruction, plus a workflow nobody would build. |
| Drop automated moderation entirely | Loses the safety property — unreviewed content would go straight live. |
| An LLM moderation pass | Better judgement, but adds cost and latency to every publish, and the LLM path is already the slowest thing here (ADR 003 territory). Worth revisiting if volume justifies it. |

**Revisit when:** the queue grows faster than it is drained, someone publishes
something genuinely abusive that 10 occurrences didn't catch, or story length
grows enough that the counting cost matters.
