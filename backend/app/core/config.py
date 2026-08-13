from pydantic_settings import BaseSettings,SettingsConfigDict
import os
class Settings(BaseSettings):
    DATABASE_URL: str
    # TEST_DB_BASE: str
    SECRET_KEY: str
    JWT_SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    MAIL_SERVER: str
    MAIL_PORT: int
    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM: str
    MAIL_FROM_NAME: str
    ADMIN_USERNAME:str
    ADMIN_EMAIL:str
    ADMIN_PASSWORD:str
    FRONTEND_URL: str  # e.g. "https://yourdomain.com"
    CLOUDINARY_CLOUD_NAME: str
    CLOUDINARY_API_KEY: str
    CLOUDINARY_API_SECRET: str
      # Google OAuth
    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None
    GOOGLE_REDIRECT_URI: str | None = None 
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "google")   # "google" | "openai"
    # Default must be a currently-valid model. "gemini-pro-2.5" is retired and
    # 404s — prod only worked because the Cloud Run env var overrides this. If
    # that override is ever dropped, generation breaks silently, so keep the
    # default itself valid.
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini-flash-latest")
    GOOGLE_API_KEY: str | None = os.getenv("GOOGLE_API_KEY")
    OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.8"))
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "8192"))
    LLM_TIMEOUT: float = float(os.getenv("LLM_TIMEOUT", "120"))  # seconds — long stories need it

    # Redis — used by the rate limiter, cache-aside layer, and (future) Celery
    # broker + WS pub/sub backplane. See UPGRADE_PLAN.md Phase 1.
    REDIS_URL: str = "redis://localhost:6379/0"

    ENVIRONMENT: str = "development"    # host sets ENVIRONMENT=production in prod

    # ----- Celery execution mode (COST DECISION — see docs/adr/001) -----
    # /** WHY: a Celery worker is a *polling* consumer — it has no HTTP surface,
    #     so Cloud Run can never scale it to zero (nothing would wake it to poll
    #     the broker). Running it needs `--min-instances=1 --no-cpu-throttling`,
    #     i.e. a CPU billed 24/7 — the single largest line item in this stack,
    #     for a personal project that is idle most of the day. **/
    # /** WHAT: when true, `.delay()` executes the task INLINE in the calling
    #     process instead of enqueueing it. No worker, no broker traffic, $0.
    #     Every enqueue site already commits BEFORE calling `.delay()`, so the
    #     task still sees a committed row — inline execution is safe here. **/
    # /** TRADE-OFF (accepted deliberately): the task's latency moves into the
    #     request (story publish now waits on the LLM moderation call), and
    #     Celery's retry/backoff is lost — eager mode does not retry. Correct
    #     answer at scale is push delivery (Cloud Tasks -> HTTP endpoint), which
    #     keeps scale-to-zero AND async execution. Documented, not forgotten. **/
    CELERY_TASK_ALWAYS_EAGER: bool = False

    # ----- Observability -----
    # JSON logs + Sentry only make sense in prod; dev stays human-readable and
    # Sentry-free. SENTRY_DSN unset => Sentry is simply not initialized.
    LOG_LEVEL: str = "INFO"
    SENTRY_DSN: str | None = None
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',                # ignore unknown env vars (prevents “extra_forbidden”)
        case_sensitive=False
    )

    @property
    def IS_DEV(self) -> bool:
        return self.ENVIRONMENT.lower() != "production"

settings = Settings()
