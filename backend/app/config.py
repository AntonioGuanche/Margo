"""Application configuration via environment variables."""

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # --- Database ---
    database_url: str = "postgresql+asyncpg://margo:margo_dev@localhost:5432/margo"

    @field_validator("database_url")
    @classmethod
    def fix_database_scheme(cls, v: str) -> str:
        """Railway injects postgresql:// — asyncpg needs postgresql+asyncpg://."""
        if v.startswith("postgres://"):
            v = v.replace("postgres://", "postgresql+asyncpg://", 1)
        elif v.startswith("postgresql://"):
            v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v
    db_pool_size: int = 20
    db_max_overflow: int = 10

    # --- Auth ---
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 24 * 7  # 1 week
    magic_link_expiry_minutes: int = 15

    # --- Anthropic (Sprint 3+) ---
    anthropic_api_key: str = ""

    # --- Cloudflare R2 (Sprint 4+) ---
    r2_account_id: str = ""
    r2_access_key: str = ""
    r2_secret_key: str = ""
    r2_bucket: str = "margo-invoices"
    r2_public_url: str = ""

    # --- Email (Sprint 5+) ---
    resend_api_key: str = ""

    # --- Stripe (Sprint 8) ---
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""

    # --- App ---
    frontend_url: str = "http://localhost:5173"
    environment: str = "development"


settings = Settings()
