# Deploy runbook — blog_proj (Cloud Run)

**Read the migration section before every deploy.** Migrations are no longer
applied automatically on container start, so the order below is not optional.

---

## Why migrations are a deploy STEP, not a boot step

`backend/entrypoint.sh` runs `python -m app.seed` (alembic upgrade + seed) unless
`SKIP_MIGRATIONS=true`. Leaving it on boot has two problems:

1. **Slow.** It costs ~10s of every cold start re-checking migrations that are
   already applied. Measured cold start was 23.6s, of which migrations+seed were
   ~10s (boot log: migrations start → app start = 10s).
2. **Unsafe.** The service is `maxScale=20`. Several instances can cold-start at
   once and each would run `alembic upgrade head` *and* the admin seed
   concurrently — racing DDL, and racing the seed against unique constraints. It
   only looks harmless because alembic on an up-to-date DB is a no-op.

So `SKIP_MIGRATIONS=true` is the correct setting — but it transfers the
responsibility to this runbook.

---

## Deploy sequence

### 0. Pre-flight
```bash
# authenticated gcloud lives in WSL, not Windows
wsl.exe -e bash -lc 'gcloud config set project gen-lang-client-0452867537'

# tests must be green before an image is built
docker compose up -d
docker compose exec --user root backend sh -c 'rm -rf /app/tests'
docker compose cp ./backend/tests backend:/app/tests
docker compose exec -e TEST_DB_BASE="postgresql://test_user:test_password@db:5432/quill_test" \
  -e NO_NETWORK=0 backend python -m pytest tests/ -m "not e2e"
```

### 1. Check what prod's schema is at
```bash
# local head
ls backend/alembic/versions/ | sort

# prod current — run from a machine with psql, or Neon's SQL editor:
#   select version_num from alembic_version;
```
If prod's `version_num` == local head, skip step 2.

### 2. Apply migrations FIRST (before the new image is serving)
```bash
# MIGRATION_DATABASE_URL must be the DIRECT (non-pooled) Neon endpoint.
# PgBouncer transaction mode breaks Alembic's advisory locks, which is why
# database-url is pooled and migration-database-url deliberately is not.
cd backend
MIGRATION_DATABASE_URL="<direct neon url>" python -m alembic upgrade head
```
⚠ **Never run migrations from a local `docker compose` shell without pinning
`MIGRATION_DATABASE_URL`.** `backend/.env` points at PROD; compose overrides it to
the local DB. Getting this wrong once already applied a migration to production.

### 3. Build and deploy
```bash
gcloud builds submit backend/ --tag us-central1-docker.pkg.dev/gen-lang-client-0452867537/backend-repo/api:vNN

gcloud run deploy quill-backend \
  --image us-central1-docker.pkg.dev/gen-lang-client-0452867537/backend-repo/api:vNN \
  --region us-central1 \
  --timeout=300 \
  --update-env-vars=ENVIRONMENT=production,SKIP_MIGRATIONS=true,CELERY_TASK_ALWAYS_EAGER=true
```

**`--timeout=300` is stated explicitly on purpose.** 300s happens to be the
Cloud Run default, so this changes nothing today — but under eager mode the
service timeout is the last bound on any inline task
(`task_time_limit` is enforced by a worker, and there is no worker), so it
should be a recorded decision rather than a platform default nobody chose.

It cannot be lowered far: this service also serves **AI streaming generation**,
whose own `LLM_TIMEOUT` is 120s, so a long story legitimately holds a request
for around two minutes. ~180s is the practical floor. Email no longer reaches
this bound at all — it is capped by `SMTP_TOTAL_BUDGET_SECONDS` (12s) — see
[ADR 003](adr/003-inline-smtp-retry.md).

⚠ **`--update-env-vars`, never `--set-env-vars`.** `--set-env-vars` REPLACES the
whole env list — it would silently delete the ~13 other literal vars the service
needs (`LLM_PROVIDER`, `LLM_MODEL`, `FRONTEND_URL`, `GOOGLE_REDIRECT_URI`,
`MAIL_*`, `CLOUDINARY_*`, `ADMIN_*`) and the app would boot broken or not at all.
Secrets (`--set-secrets`) are a separate list and are unaffected either way.

**Both new env vars matter:**
- `SKIP_MIGRATIONS=true` — cold start drops ~10s; migrations are step 2's job.
- `CELERY_TASK_ALWAYS_EAGER=true` — **required.** The Celery worker was deleted
  (see `adr/001-workerless-inline-tasks.md`). Without this flag four call sites
  enqueue to a broker nobody consumes, and all fail **silently**:
  story publish (stays `pending` forever), signup verification email, webhook
  delivery, support-ticket escalation.

### 4. Post-deploy smoke test
```bash
BASE=https://quill-backend-25ni6nvjaq-uc.a.run.app
curl -s -o /dev/null -w "root    %{http_code}\n"      $BASE/
curl -s -o /dev/null -w "list    %{http_code}\n"      "$BASE/api/v1/stories/?limit=1"
curl -s -o /dev/null -w "legacy  %{http_code}\n"      "$BASE/stories/?limit=1"
curl -s -o /dev/null -w "search  %{http_code}\n"      "$BASE/api/v1/stories/search?q=test"
curl -s -o /dev/null -w "metrics %{http_code}\n"      $BASE/metrics
```

⚠ **Do NOT smoke-test `/healthz` through the public URL.** Cloud Run's ingress
**reserves `/healthz`** and answers it itself with a Google-branded HTML 404 —
the request never reaches the container. The route is fine and *does* work
in-container, which is why the Dockerfile `HEALTHCHECK` and `docker compose`
healthcheck both pass. Verified by the response body: ours is problem+json,
that 404 is Google's. Use `/` for external liveness (the keep-warm job does).
Then, in the app: **publish a story as a non-moderator and confirm it appears** —
that is the only end-to-end proof that `CELERY_TASK_ALWAYS_EAGER` took effect.

---

## The `/api/v1` cutover — one-time, this deploy only

Routers moved under `/api/v1`. Frontend and backend **must ship together**, and
two external contracts need updating:

1. **Google OAuth** — the callback is now `/api/v1/auth/google/callback`. Update
   the `GOOGLE_REDIRECT_URI` env var **and** the Authorized Redirect URI in the
   Google Cloud Console OAuth client. Google login breaks until both match.
2. **Refresh cookie path** — now `/api/v1/auth` (`COOKIE_PATH` in `routes/auth.py`).
   Existing sessions will need a re-login.

---

## Cost guardrails currently in place

| Thing | State |
|---|---|
| Celery worker (`quill-worker`) | **Deleted.** Was `--min-instances=1 --no-cpu-throttling` = a vCPU billed 24/7. See ADR 001. |
| `quill-backend` scaling | `minScale` unset (scales to 0), `maxScale=20`, CPU throttled → billed only while processing a request |
| Keep-warm | Cloud Scheduler `quill-keepwarm` GETs `/` every 5 min, 08:00–22:00 IST. Free: idle instances cost nothing when CPU-throttled. Stops demo links hitting a 23s cold start. |
| Budget alert | `quill-cost-guardrail`, $5/mo, alerts at 50% / 90% |
| `SKIP_MIGRATIONS=true` | **Already set** on the service (rev 00034). Boot no longer runs alembic. |
| `CELERY_TASK_ALWAYS_EAGER=true` | **Already set**, but **inert** until the new code ships — the deployed image predates the setting. |

**Because both flags are already set, the single biggest deploy risk is now
step 2:** if you deploy the new image without running `alembic upgrade head`
first, nothing will migrate for you and `stories.row_version` alone will 500
every story query. Step 2 is not optional.

**Do not** reintroduce `--min-instances=1` or `--no-cpu-throttling` without a
reason; together they are what made this stack cost money.
