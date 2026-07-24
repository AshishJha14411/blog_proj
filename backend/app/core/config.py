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
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini-pro-2.5")
    GOOGLE_API_KEY: str | None = os.getenv("GOOGLE_API_KEY")
    OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.8"))
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "2048"))
    LLM_TIMEOUT: float = float(os.getenv("LLM_TIMEOUT", "30"))  # seconds

    # Redis — used by the rate limiter, cache-aside layer, and (future) Celery
    # broker + WS pub/sub backplane. See UPGRADE_PLAN.md Phase 1.
    REDIS_URL: str = "redis://localhost:6379/0"

    ENVIRONMENT: str = "development"    # host sets ENVIRONMENT=production in prod
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
