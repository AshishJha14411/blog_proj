"""Database engines and session factories.

Two engines on purpose:
- SYNC (`engine` / `SessionLocal`) — used by Celery tasks, the DB log handler,
  and the seed/alembic path. Celery isn't async and those code paths run
  outside the request event loop, so they keep a plain blocking session.
- ASYNC (`async_engine` / `AsyncSessionLocal`) — used by the FastAPI request
  path via `get_async_db`. `async def` routes await their queries, so one
  worker process serves many concurrent IO-bound requests instead of parking a
  thread per request.

The async URL is derived from DATABASE_URL by swapping the driver to asyncpg.
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings

SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

# --- Sync (Celery tasks, DB log handler, seed) ---
# /** WHY pool_pre_ping: managed Postgres closes idle connections (Neon suspends
#     compute; PgBouncer recycles), and a pooled connection can also be killed
#     server-side by a schema migration. Without a pre-ping the next request
#     grabs that dead connection and 500s with
#     `psycopg2.OperationalError: SSL connection has been closed unexpectedly`.
#     Observed in production immediately after a migration. pre_ping costs one
#     cheap round-trip per checkout and turns that class of error into a
#     transparent reconnect. **/
# /** WHY pool_recycle: bound connection age below the provider's idle timeout so
#     connections are retired proactively rather than discovered dead. **/
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    echo=settings.IS_DEV,
    future=True,
    pool_pre_ping=True,
    pool_recycle=300,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def _to_async_url(url: str) -> str:
    """Rewrite a libpq/psycopg URL to the asyncpg driver.

    Also drops `sslmode`/`channel_binding` query params — those are libpq
    spellings asyncpg doesn't parse; SSL is instead passed via connect_args.
    """
    # normalize any existing driver prefix to bare postgresql://
    if url.startswith("postgresql+"):
        url = "postgresql://" + url.split("://", 1)[1]
    url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if "?" in url:
        url = url.split("?", 1)[0]
    return url


# asyncpg wants SSL as a connect arg, not a URL param. Enable it for managed
# hosts (Neon) and leave it off for the local docker Postgres.
_needs_ssl = "sslmode=require" in SQLALCHEMY_DATABASE_URL or "neon.tech" in SQLALCHEMY_DATABASE_URL
_async_connect_args = {"ssl": True} if _needs_ssl else {}

# --- asyncpg behind a connection pooler (PgBouncer) ---
# /** WHY: asyncpg uses server-side PREPARED STATEMENTS for every query, and
#     SQLAlchemy's asyncpg dialect caches them. PgBouncer in *transaction*
#     pooling mode hands a different backend connection to each transaction, so a
#     cached statement prepared on one connection is missing (or duplicated) on
#     the next — producing DuplicatePreparedStatementError / InvalidSQLStatement
#     under load. Neon's pooled endpoint (`-pooler` in the host) is PgBouncer. **/
# /** WHY-THIS-WAY: DATABASE_URL is deliberately the POOLED endpoint (a
#     serverless app must not open direct connections — see docs/DEPLOY.md), so
#     the cache has to be off rather than the pooler swapped out. Setting
#     asyncpg's `statement_cache_size` to 0 makes it issue one-shot statements
#     instead of caching named ones, which is what PgBouncer can actually
#     forward. Cost is re-planning each query — correctness first. **/
# /** NOTE `statement_cache_size` goes in connect_args because it is an
#     *asyncpg.connect* parameter. Do NOT pass `prepared_statement_cache_size`
#     to create_async_engine: SQLAlchemy 2.0.41's asyncpg dialect does not accept
#     it and raises `TypeError: Invalid argument(s) ... sent to create_engine()`
#     at import time — which crashes the container on boot. Verified against
#     `inspect.signature(PGDialect_asyncpg.__init__)`. **/
# /** NOTE: invisible locally — plain Postgres has no pooler in front of it — so
#     this can only be validated against a real deployment (canary), not tests. **/
_is_pooled = "pooler" in SQLALCHEMY_DATABASE_URL or "pgbouncer" in SQLALCHEMY_DATABASE_URL
if _is_pooled:
    _async_connect_args["statement_cache_size"] = 0

async_engine = create_async_engine(
    _to_async_url(SQLALCHEMY_DATABASE_URL),
    echo=settings.IS_DEV,
    future=True,
    connect_args=_async_connect_args,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False,
)
