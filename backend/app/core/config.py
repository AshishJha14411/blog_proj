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
    # /** WHY THESE ARE ENV-TUNABLE: the SMTP send runs INLINE inside the signup
    #     request (no worker — ADR 001), and `task_time_limit` is enforced by a
    #     Celery worker, so under eager mode it does nothing. That left the Cloud
    #     Run service timeout (300s) as the only bound on a hung mail provider.
    #     These two put the bound back where it belongs — at the call site — and
    #     make it changeable without a redeploy when a provider misbehaves.
    #
    #     SMTP_TIMEOUT_SECONDS       caps ONE attempt (socket connect + commands).
    #     SMTP_TOTAL_BUDGET_SECONDS  caps ALL attempts plus their backoff, so
    #                                retries can never multiply into a long block.
    #     The budget is the number that matters: it is the worst case a user can
    #     wait on signup because of email. See docs/adr/003-inline-smtp-retry.md. **/
    SMTP_TIMEOUT_SECONDS: float = float(os.getenv("SMTP_TIMEOUT_SECONDS", "5"))
    SMTP_TOTAL_BUDGET_SECONDS: float = float(os.getenv("SMTP_TOTAL_BUDGET_SECONDS", "12"))

    # /** HOW MANY profane words before a story is held for review.
    #     Flagging on the FIRST hit made length the real filter: profanity is
    #     counted per word, so the odds of at least one hit rise with word
    #     count, and long stories were flagged essentially every time while
    #     short ones sailed through. A threshold measures saturation instead,
    #     which is roughly length-independent — and it is tunable without a
    #     redeploy when the right number turns out to be different.
    #     See docs/adr/004-moderation-holds-not-rejects.md. **/
    MODERATION_PROFANITY_THRESHOLD: int = int(os.getenv("MODERATION_PROFANITY_THRESHOLD", "10"))
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
    # /** WHY flash-LITE and not flash: `gemini-flash-latest` became unusable —
    #     measured 43s to first streaming chunk, and in production it exceeded
    #     the 120s deadline outright:
    #         ws_support: LLM error: Gemini streaming error: 504 Deadline Exceeded
    #     Support chat looked broken (socket fine, message accepted, no reply)
    #     and story generation was crawling. Same measurement on flash-lite:
    #     **1.0s to first chunk**, ~40x faster, and no deadline failures.
    #
    #     Lite is a smaller model, so prose quality is lower — accepted, because
    #     a fast answer beats a 504. Revisit if story quality suffers visibly.
    #
    #     NOTE: `gemini-2.5-flash-lite` and `gemini-2.0-flash-lite` both 404 —
    #     retired for new users. The `-latest` alias is the one that resolves. **/
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini-flash-lite-latest")
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
