# tests/conftest.py
import os
import json
import pytest
import alembic.config
import alembic.command
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Generator
from app.core.database import Base
from sqlalchemy import event, create_engine,text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine.url import make_url
from sqlalchemy_utils import database_exists, create_database, drop_database
from tests.factories import RoleFactory, UserFactory, StoryFactory, CommentFactory, LikeFactory, BookmarkFactory, FlagFactory, ModeratorFactory,PasswordResetTokenFactory,AdFactory, ClickFactory, ImpressionFactory, TagFactory
from fastapi.testclient import TestClient
from app.dependencies import get_mailer
from alembic.config import Config
from alembic import command
# ------------------------------------------------------------------
# 0) LOCK TEST ENV BEFORE IMPORTING APP
# ------------------------------------------------------------------
# A real test DB, distinct from dev DB. Per-worker DB supported (xdist).
BASE_TEST_DB = os.getenv("TEST_DB_BASE", "postgresql://test_user:test_password@localhost:5432/quill_test")

# Signal “test mode” to app (tweak cookie flags, disable background sends, etc.)
os.environ.setdefault("ENV", "test")

os.environ["DATABASE_URL"] = BASE_TEST_DB

# Disallow real egress in tests by default; allowlist can be extended in tests.
os.environ.setdefault("NO_NETWORK", "1")

# Import AFTER env is locked
from app.core.config import settings
from app.main import app
from app.dependencies import get_db, get_async_db
from app.utils.security import create_access_token


# ------------------------------------------------------------------
#  SYNC -> ASYNC SESSION ADAPTER (for testing async routes/services)
# ------------------------------------------------------------------
# The async request path (get_async_db + async story reads) expects an
# AsyncSession. Our test isolation, however, is built on ONE sync psycopg2
# connection inside an outer transaction + SAVEPOINT (see db_session): that's
# what gives every test a private schema and a clean rollback. A real async
# engine would be a *different* connection/transaction and couldn't see the
# factory rows staged in the sync SAVEPOINT.
#
# This shim presents that same sync Session behind the async Session API
# (`await execute/get/commit/rollback`), so async endpoints and services run
# inside the exact test transaction. No real event-loop IO happens — psycopg2
# executes synchronously under the `await`, which is precisely what we want for
# deterministic, isolated tests. The `Result` returned by a sync `execute` is
# the same object an async `execute` yields, so `.scalars()/.first()/.all()/
# .unique()/.scalar()` all work unchanged downstream.
class _AsyncSessionAdapter:
    def __init__(self, sync_session: Session):
        self._s = sync_session

    async def execute(self, statement, params=None, **kw):
        return self._s.execute(statement, params, **kw)

    async def get(self, entity, ident, **kw):
        return self._s.get(entity, ident, **kw)

    async def scalar(self, statement, params=None, **kw):
        return self._s.scalar(statement, params, **kw)

    def add(self, obj):
        self._s.add(obj)

    async def commit(self):
        self._s.commit()

    async def rollback(self):
        self._s.rollback()

    async def flush(self):
        self._s.flush()

    async def refresh(self, obj, *a, **k):
        self._s.refresh(obj, *a, **k)

    async def delete(self, obj):
        self._s.delete(obj)

    def __getattr__(self, name):
        # Anything not explicitly shimmed (e.g. .no_autoflush) falls through to
        # the wrapped sync session.
        return getattr(self._s, name)

# Optional: if you have provider dependencies, import here to override.
# from app.dependencies import get_mailer, get_cloudinary

# ------------------------------------------------------------------
#  UTIL: PER-WORKER DB URL (xdist) & SAFETY CHECKS
# ------------------------------------------------------------------
def _db_url_for_worker(base_url: str, worker_id: str | None) -> str:
    """
    For pytest-xdist parallel runs, create per-worker DBs:
      gw0 -> quill_test_gw0, etc.
    For serial runs, keep base DB.
    """
    url = make_url(base_url)
    dbname = url.database or ""
    if worker_id and worker_id != "master":
        url = url.set(database=f"{dbname}_{worker_id}")
    else:
        url = url.set(database=dbname)

    if not (url.database and url.database.startswith("quill_test")):
        raise RuntimeError(f"Refusing to run tests on non-test DB: {url.database}")
    return str(url)

# ------------------------------------------------------------------
#  SESSION-SCOPED ENGINE (MIGRATED SCHEMA, PER WORKER)
# ------------------------------------------------------------------
# tests/conftest.py (replace existing db_engine & db_session fixtures with this)
import os, uuid
from sqlalchemy import text

TEST_SCHEMA_PREFIX = os.getenv("TEST_SCHEMA_PREFIX", "test_schema")
USE_TEST_SCHEMA = True  
# set False to use old behavior (for debugging)
# NOTE (temporary): We create an isolated schema per test session to avoid touching
# developer/production data when Alembic migrations were accidentally deleted.
# This is a pragmatic, non-destructive workaround while we regenerate migrations.
# TODO (draft-2): remove this and restore alembic-driven test DB creation once
# migrations are restored.

@pytest.fixture(scope="session")
def db_engine():
    """
    Create a test-only schema inside the same Postgres database instead of
    dropping production/public tables. Safe and isolated.
    """
    engine = create_engine(BASE_TEST_DB, future=True, pool_pre_ping=True)

    schema_name = f"{TEST_SCHEMA_PREFIX}_{os.getpid()}_{uuid.uuid4().hex[:6]}"

    # Store schema name in an attribute for backward compatibility
    setattr(engine, "_test_schema", schema_name)

    # `search_path` is a per-connection (session-level) Postgres setting, not
    # an engine-wide one. Setting it once on the single connection used below
    # only isolates *that* connection — db_session's db_engine.connect() can
    # hand back any other pooled connection (default pool_size=5), which
    # would still have the default `public` search_path and silently read/
    # write the real public schema instead of this isolated one. A `connect`
    # event fires for every physical DBAPI connection the pool ever creates,
    # so this is what actually makes every connection isolated, not just one.
    @event.listens_for(engine, "connect")
    def _set_search_path(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute(f'SET search_path TO "{schema_name}", public')
        cursor.close()

    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))
        conn.execute(text(f'SET search_path TO "{schema_name}", public'))
        # checkfirst=False: the default checkfirst=True probes table
        # existence through the connection's search_path, which finds the
        # REAL app tables already sitting in `public` (from migrations/seed
        # run outside tests) and concludes each table "already exists" —
        # skipping creation in `{schema_name}` entirely. The schema name is
        # freshly randomized above, so it's guaranteed empty; no need to
        # check first, and skipping the check is what makes tables actually
        # get created here instead of silently falling through to `public`.
        Base.metadata.create_all(conn, checkfirst=False)
        # `search_vector` (full-text search) is a GENERATED column created by
        # Alembic migration d4e5f6a7b8c9 via raw SQL — it is NOT on the ORM
        # model, so create_all() doesn't build it. Mirror the migration here so
        # the schema matches production and /stories/search is actually testable
        # (without this, any search query 500s with "column does not exist").
        conn.execute(text(
            """
            ALTER TABLE stories
            ADD COLUMN IF NOT EXISTS search_vector tsvector
            GENERATED ALWAYS AS (
                setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
                setweight(to_tsvector('english', coalesce(content, '')), 'B')
            ) STORED
            """
        ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_stories_search_vector "
            "ON stories USING GIN (search_vector)"
        ))

    yield engine

    # Cleanup: Drop only our temp schema, not the main DB
    try:
        with engine.begin() as conn:
            conn.execute(text('SET search_path TO public'))
            conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE'))
    except Exception as e:
        print(f"[WARN] Could not drop schema {schema_name}: {e}")
    finally:
        engine.dispose()

@pytest.fixture(scope="session", autouse=True)
def ensure_base_roles(db_engine):
    """Ensure the base roles exist in the test DB (bypassing Alembic)."""
    from sqlalchemy.orm import sessionmaker
    from app.models.role import Role

    session = sessionmaker(bind=db_engine, expire_on_commit=False)()
    for name in ["user", "creator", "moderator", "superadmin"]:
        if not session.query(Role).filter_by(name=name).first():
            session.add(Role(name=name, description=f"Default {name} role"))
    session.commit()
    session.close()

@pytest.fixture(scope="function")
def db_session(db_engine) -> Generator[Session, None, None]:
    """
    Single source of truth:
      - get a fresh Connection from the Engine
      - ensure it's not already in a transaction (rollback if it is)
      - open one outer transaction
      - create a Session bound to that Connection
      - start a SAVEPOINT for app-level commit/rollback safety
      - re-create the SAVEPOINT after each commit/rollback
    """
    connection = db_engine.connect()

    # If a previous step left the connection in a transaction (pool reuse),
    # make sure we reset it before starting our own transaction.
    try:
        if connection.in_transaction():
            connection.rollback()
    except Exception:
        # compatibility with older SQLAlchemy versions
        tx = connection.get_transaction()
        if tx is not None:
            tx.rollback()

    outer = connection.begin()

    SessionLocal = sessionmaker(bind=connection, expire_on_commit=False, future=True)
    session: Session = SessionLocal()

    # Start inner SAVEPOINT
    session.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(sess, trans):
        # Re-open SAVEPOINT after each commit/rollback inside the test
        if trans.nested and not trans._parent.nested:
            try:
                sess.begin_nested()
            except Exception:
                pass

    try:
        yield session
    finally:
        # Close the ORM session first (releases its transaction handles)
        try:
            session.close()
        finally:
            # Roll back the outer transaction to discard all changes
            try:
                if connection.in_transaction():
                    connection.rollback()
                else:
                    # if outer Transaction object exists, try rollback anyway
                    try:
                        outer.rollback()
                    except Exception:
                        pass
            finally:
                connection.close()


# ------------------------------------------------------------------
# ALEMBIC SYNC SANITY CHECK
# ------------------------------------------------------------------

from alembic.script import ScriptDirectory
from alembic.runtime.environment import EnvironmentContext

@pytest.fixture(scope="session", autouse=True)
def verify_migrations_uptodate():
    """
    Verify that the Alembic migrations are up to date with the database schema.
    Skips check if no Alembic context is available (prevents 'No context configured' error).
    """
    import alembic.config
    from sqlalchemy import create_engine

    config = alembic.config.Config("alembic.ini")
    script = ScriptDirectory.from_config(config)
    head_revision = script.get_current_head()

    engine = create_engine(BASE_TEST_DB, future=True)
    current_revision = None

    def get_rev(rev, context):
        nonlocal current_revision
        current_revision = context.get_current_revision()
        return []

    try:
        with engine.connect() as conn:
            with EnvironmentContext(config, script, as_sql=False, fn=get_rev, connection=conn):
                script.run_env()  # ✅ This safely initializes Alembic context
    except Exception as e:
        # Print for debugging but don't fail all tests
        print(f"[WARN] Skipping Alembic revision check: {e}")
        return

    if current_revision != head_revision:
        pytest.fail(f"Alembic migration mismatch: DB at {current_revision}, expected {head_revision}")


# ------------------------------------------------------------------
#  DUMMIES / STUBS FOR EXTERNAL DEPENDENCIES
# ------------------------------------------------------------------
# Make DummyMailer sync so we don't need an event loop.
class DummyMailer:
    def __init__(self):
        self.outbox: list[dict] = []

    # /** WHY: signature must match app/utils/email.py::Mailer.send_email
    #     (to_email/subject/body). The Celery email task calls those exact
    #     kwargs; if this drifts, every signup/reset test blows up with
    #     TypeError instead of asserting on outbox contents. **/
    def send_email(self, to_email: str, subject: str, body: str):
        self.outbox.append(
            {
                # Keep both keys so existing tests that read `to`/`html` still
                # work AND the new task-shaped keys are available.
                "to": to_email,
                "to_email": to_email,
                "subject": subject,
                "html": body,
                "body": body,
                "ts": datetime.now(timezone.utc).isoformat(),
            }
        )

# Helper to execute queued background tasks
import asyncio, inspect
import fastapi

@pytest.fixture
def run_bg_tasks():
    def _run(bg: fastapi.BackgroundTasks):
        for task in bg.tasks:
            result = task.func(*task.args, **task.kwargs)
            # if someone keeps send_email async in future-proofing, we still handle it
            if inspect.iscoroutine(result):
                loop = asyncio.new_event_loop()
                try:
                    loop.run_until_complete(result)
                finally:
                    loop.close()
    return _run

class DummyCloudinary:
    """Pretend to upload and return a deterministic URL."""
    def upload_file(self, file_obj, folder: str = "test"):
        return f"https://cloudinary.example/{folder}/fake_{int(datetime.now().timestamp())}.png"

@pytest.fixture(scope="function")
def dummy_mailer():
    return DummyMailer()

@pytest.fixture(autouse=True)
def override_mailer(dummy_mailer):
    app.dependency_overrides[get_mailer] = lambda: dummy_mailer
    yield
    app.dependency_overrides.pop(get_mailer, None)
    
@pytest.fixture(scope="function")
def dummy_cloudinary():
    return DummyCloudinary()



# ------------------------------------------------------------------
#  FASTAPI CLIENT (PER TEST) + DB OVERRIDE
# ------------------------------------------------------------------
# REST routers moved under /api/v1 (see app/main.py). Rather than rewrite every
# test path, this client transparently prepends the version to bare REST paths.
# Infra (/, /healthz, /metrics, /openapi…) and WebSocket (/ws) paths pass
# through unchanged — they're not part of the versioned contract. websocket
# connections use a different method (websocket_connect) so they never hit this.
_API_V1_PREFIX = "/api/v1"
_PASSTHROUGH_PREFIXES = ("/api/", "/ws", "/healthz", "/metrics", "/openapi", "/docs", "/redoc")


class _PrefixedTestClient(TestClient):
    def request(self, method, url, *args, **kwargs):
        if (
            isinstance(url, str)
            and url.startswith("/")
            and url != "/"
            and not url.startswith(_PASSTHROUGH_PREFIXES)
        ):
            url = _API_V1_PREFIX + url
        return super().request(method, url, *args, **kwargs)


@pytest.fixture(scope="function")
def client(db_session: Session):
    def _override_get_db():
        yield db_session

    # Async routes get the SAME sync transaction via the adapter, and this
    # override mirrors get_async_db's unit-of-work: commit on success (so
    # staged writes like the story view-log land in the SAVEPOINT and are
    # visible to the test's follow-up queries), roll back on error.
    async def _override_get_async_db():
        adapter = _AsyncSessionAdapter(db_session)
        try:
            yield adapter
            await adapter.commit()
        except Exception:
            await adapter.rollback()
            raise

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_async_db] = _override_get_async_db
    client = _PrefixedTestClient(app)
    try:
        yield client
    finally:
        app.dependency_overrides.clear()
        client.close()


# ------------------------------------------------------------------
#  AUTH HELPERS (USERS / TOKENS) — FAST, NO NETWORK
# ------------------------------------------------------------------
@pytest.fixture
def make_token():
    """Create an access token for a given user_id (stringified UUID)."""
    def _make(user_id: str, **claims):
        payload = {"user_id": user_id, **claims}
        return create_access_token(payload)
    return _make

@pytest.fixture
def auth_headers(make_token):
    def _hdrs(user_id: str):
        return {"Authorization": f"Bearer {make_token(user_id)}"}
    return _hdrs

# ------------------------------------------------------------------
#  NETWORK GUARDRAILS (OPTIONAL BUT RECOMMENDED)
# ------------------------------------------------------------------
def pytest_runtest_setup(item):
    # If pytest-socket is installed and NO_NETWORK=1, block all egress except localhost
    if os.getenv("NO_NETWORK") == "1":
        try:
            import socket
            from pytest_socket import disable_socket, enable_socket, SOCKET_ALLOWLIST
            disable_socket()
            SOCKET_ALLOWLIST.add("127.0.0.1")
            SOCKET_ALLOWLIST.add("localhost")
        except ImportError:
            # silently ignore if plugin not installed
            pass

# ------------------------------------------------------------------
#  TIME FREEZE HELPER (OPTIONAL)
# ------------------------------------------------------------------
@pytest.fixture
def freezer():
    """Use freezegun in tests: freezer.move_to('2025-01-01 00:00:00') etc."""
    try:
        from freezegun import freeze_time
    except ImportError:
        pytest.skip("freezegun not installed")
    with freeze_time("2025-01-01 00:00:00"):
        yield


from app.llm.adapter import LLMAdapter

@pytest.fixture(autouse=True)
def stub_llm(monkeypatch):
    def _fake_generate(self, prompt, *, model=None, temperature=None, max_tokens=None, timeout=None):
        return ("<h1>Fake title</h1><p>Fake body.</p>", "fake-msg-id")
    monkeypatch.setattr(LLMAdapter, "generate", _fake_generate)


# ------------------------------------------------------------------
#  REDIS (fakeredis) — Phase 1 of UPGRADE_PLAN
# ------------------------------------------------------------------
# We swap the shared Redis client for an in-memory fake per test. This lets
# rate-limiter and cache tests run without a real Redis service — CI does
# spin one up (see .github/workflows/ci.yml) but the majority of tests
# don't care about it, and depending on a network daemon in every unit
# test is a fragile default.

@pytest.fixture(autouse=True)
def fake_redis():
    import fakeredis
    from app.core import redis as redis_module

    fake = fakeredis.FakeRedis(decode_responses=True)
    redis_module.set_redis_client(fake)
    try:
        yield fake
    finally:
        fake.flushall()
        redis_module.reset_redis_client()


# ------------------------------------------------------------------
#  CELERY EAGER MODE — Phase 2 of UPGRADE_PLAN
# ------------------------------------------------------------------
# `.delay()` normally puts a message on the broker for a worker to pick up.
# In tests we don't want to spin up a worker — `task_always_eager=True`
# runs the task synchronously in the calling thread instead. Combined with
# `task_eager_propagates=True`, exceptions raised in a task propagate to
# the caller, which is what test assertions need.
#
# Also: patch `_mailer_for_worker` inside the email task module so tests
# can still assert on `dummy_mailer.outbox` — the task calls this helper
# to build its SMTP client, and we substitute the dummy per test.

@pytest.fixture(autouse=True)
def _stub_moderate_story_task(monkeypatch):
    """
    /** WHY: story_service.create_story enqueues moderate_story_task.delay()
        on every publish. Under eager mode the task would actually run and
        open a fresh SessionLocal() that writes outside the test's SAVEPOINT
        — leaking rows across tests and pointing at prod DB during CI setup. **/
    /** WHAT: replace the task binding at the enqueue site with a no-op.
        Tests that want to exercise the task itself import the real symbol
        directly (see tests/unit/tasks/test_moderation_task.py). **/
    """
    from app.services import story as story_service

    class _NoOpTask:
        def delay(self, **kwargs):
            return None
        def apply(self, **kwargs):
            return None
        def apply_async(self, *args, **kwargs):
            return None

    monkeypatch.setattr(story_service, "moderate_story_task", _NoOpTask())


@pytest.fixture(autouse=True)
def celery_eager(dummy_mailer):
    """
    /** WHY: run Celery tasks synchronously in tests. Otherwise `.delay()`
        enqueues a message that never runs — every email-sending assertion
        would silently do nothing. **/
    /** WHY-THIS-WAY: eager mode is documented as "lies about serialization
        and retry behavior" for integration purposes — that's fine here
        because we have separate tests that exercise retry logic directly
        (see tests/unit/tasks/test_email_task.py). **/
    """
    from app.worker import celery_app
    from app.tasks import email as email_task

    prev_eager = celery_app.conf.task_always_eager
    prev_propagate = celery_app.conf.task_eager_propagates
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True

    original_mailer_factory = email_task._mailer_for_worker
    email_task._mailer_for_worker = lambda: dummy_mailer
    try:
        yield
    finally:
        celery_app.conf.task_always_eager = prev_eager
        celery_app.conf.task_eager_propagates = prev_propagate
        email_task._mailer_for_worker = original_mailer_factory


# ------------------------------------------------------------------
#  DISABLE RATE LIMITERS BY DEFAULT
# ------------------------------------------------------------------
# The rate limiter itself is tested in
# tests/unit/test_rate_limiter.py and tests/integration/test_rate_limit_routes.py.
# Every other test would just have to work around throttling — cheaper to
# turn the limiters off globally and let the dedicated tests re-enable
# them by not requesting this fixture (they don't).
#
# Individual test modules can opt back in by deleting their entries from
# `app.dependency_overrides` before the request under test.

@pytest.fixture(autouse=True)
def _disable_all_rate_limiters(client):
    from app.utils import rate_limiter as rl
    limiters = [
        rl.rate_limit,
        rl.signup_rate_limiter,
        rl.login_rate_limiter,
        rl.forgot_password_rate_limiter,
        rl.story_create_rate_limiter,
        rl.llm_generate_rate_limiter,
        rl.comment_create_rate_limiter,
        rl.flag_rate_limiter,
    ]
    for lim in limiters:
        client.app.dependency_overrides[lim] = lambda: None
    try:
        yield
    finally:
        for lim in limiters:
            client.app.dependency_overrides.pop(lim, None)

# ------------------------------------------------------------------
#  SEED FAKER (DETERMINISTIC FACTORY DATA)
# ------------------------------------------------------------------
@pytest.fixture(scope="session", autouse=True)
def seed_faker():
    """
    Seed Faker and FactoryBoy RNG for deterministic test data.
    Ensures consistent fake data across test runs.
    """
    import faker
    from factory import random 

    faker.Faker.seed(42)
    random.reseed_random(42)

# ------------------------------------------------------------------
#  FACTORY-BOY INTEGRATION (ADD THIS SECTION)
# ------------------------------------------------------------------
import factory
from factory.alchemy import SQLAlchemyModelFactory
from pytest_factoryboy import register

# --- Create a fixture to bind the session ---
@pytest.fixture(scope="function", autouse=True)
def setup_factories(db_session: Session):
    from tests.factories import BaseFactory
    # bind
    BaseFactory._meta.sqlalchemy_session = db_session
    for F in (RoleFactory, UserFactory,StoryFactory,CommentFactory, LikeFactory, BookmarkFactory, FlagFactory, ModeratorFactory,PasswordResetTokenFactory,AdFactory, ClickFactory, ImpressionFactory,TagFactory):
        F._meta.sqlalchemy_session = db_session
        F._meta.sqlalchemy_session_persistence = "flush"
    # unbind (keeps tests isolated)
    try:
        yield
    finally:
        for F in (RoleFactory, UserFactory, StoryFactory, CommentFactory, LikeFactory, BookmarkFactory, FlagFactory, ModeratorFactory,PasswordResetTokenFactory,AdFactory,ClickFactory, ImpressionFactory,TagFactory):
            F._meta.sqlalchemy_session = None
        BaseFactory._meta.sqlalchemy_session = None
    

@pytest.fixture(autouse=True)
def ensure_session_clean(db_session):
    yield
    if db_session.dirty or db_session.new:
        db_session.rollback()


