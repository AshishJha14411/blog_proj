# Documentation index

Start with the question you have, not the file you think you need.

## By question

| I want to… | Read |
|---|---|
| Understand what this project is and how it's built | [`../README.md`](../README.md) |
| Work on this **as an AI agent** | [`../CLAUDE.md`](../CLAUDE.md) → then the scoped file for your area |
| Get it running locally | [`DEVELOPMENT.md`](DEVELOPMENT.md) |
| Run or write tests | [`TESTING.md`](TESTING.md) |
| Debug something odd | [`GOTCHAS.md`](GOTCHAS.md) — **check here first** |
| Work on the backend | [`../backend/CLAUDE.md`](../backend/CLAUDE.md), [`../backend/README.md`](../backend/README.md) |
| Work on the frontend | [`../frontend/CLAUDE.md`](../frontend/CLAUDE.md), [`../frontend/README.md`](../frontend/README.md) |
| Look up an endpoint or the DB schema | [`../backend/README.md`](../backend/README.md) — API tables + column-level ERD |
| Deploy | [`DEPLOY.md`](DEPLOY.md) |
| Know why something was built this way | [`adr/`](adr/README.md) |
| See the performance work | [`performance.md`](performance.md) |

## Contents

```
docs/
├── README.md          # this index
├── DEVELOPMENT.md     # setup, daily workflow, exact commands, troubleshooting
├── TESTING.md         # test architecture, patterns, how to write a regression test
├── GOTCHAS.md         # traps that have already cost debugging time
├── DEPLOY.md          # production runbook (canary-first)
├── performance.md     # the latency investigation: 1.21s → 0.62s
├── adr/               # architecture decision records + index and template
├── architecture/      # animated diagram + the script that generates it
└── screenshots/       # README images + capture checklist
```

## How the docs are meant to work together

- **`README.md` files describe what is** — architecture, endpoints, schema.
  Written for a reader evaluating the project.
- **`CLAUDE.md` files describe how to work** — conventions, guardrails, the
  order to do things in. Written for whoever (or whatever) is making the change.
  Claude Code loads them automatically; the nearest one to the file you're
  editing applies.
- **`docs/` holds the process and the scar tissue** — workflow, testing,
  decisions, and the bugs that have already been paid for.

## Keeping them honest

Documentation that drifts is worse than none, because it is trusted.

- Changed an endpoint → update the API table in `backend/README.md`.
- Changed the schema → update the ERD and table in `backend/README.md`.
- Hit a trap that cost you time → add it to `GOTCHAS.md`. That file is the
  highest-value one here precisely because it is written from real failures.
- Made a decision that constrains future work → write an ADR.
- Changed a documented command → run it, then fix the doc to match reality
  rather than fixing reality to match the doc.

Claims in these docs are verified against the running system where possible
(live queries, real API calls, actual test runs). Keep that standard: if you
can't verify something, say so in the text rather than asserting it.

## Regenerating the architecture diagram

```bash
pip install -r docs/architecture/requirements.txt
python docs/architecture/generate_architecture_gif.py
```

Committed so the diagram is reproducible and editable rather than a mystery
binary. GitHub sanitises SVG animation, which is why it's a GIF.
