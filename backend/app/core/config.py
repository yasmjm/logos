import logging
from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

JWT_SECRET_MIN_LENGTH = 32
# Development only: production refuses to start without a real JWT_SECRET.
_DEV_JWT_SECRET = "logos-dev-only-insecure-jwt-secret-do-not-use"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Logos"
    app_env: Literal["development", "test", "production"] = "development"
    debug: bool = False
    database_url: str = "postgresql+psycopg://logos:logos@localhost:5433/logos"
    # Connection pool and timeouts: fail fast instead of hanging when the database is slow.
    db_pool_size: int = 5
    db_max_overflow: int = 5
    db_pool_timeout_seconds: float = 5
    db_connect_timeout_seconds: int = 3
    db_statement_timeout_ms: int = 5000
    # Shared secret for POST /incidents. When unset, ingestion rejects every request.
    ingest_api_key: SecretStr | None = None
    # Signs analyst access tokens (HS256). Required in production.
    jwt_secret: SecretStr | None = None
    jwt_expires_minutes: int = 8 * 60  # one shift
    # Resilience demo: enables /chaos (latency and simulated failures on /incidents).
    chaos_enabled: bool = False
    # Evaluator tools: POST /demo/reset and /demo/simulate (otherwise 404).
    demo_mode: bool = False
    # Comma-separated origins allowed by CORS.
    frontend_origins: str = "http://localhost:5173"

    @field_validator("ingest_api_key", "jwt_secret", mode="before")
    @classmethod
    def _blank_secret_is_unset(cls, value: object) -> object:
        # "INGEST_API_KEY=" in .env means "not configured", never an empty secret.
        return None if isinstance(value, str) and not value.strip() else value

    @model_validator(mode="after")
    def _check_production_and_cors(self) -> "Settings":
        if self.app_env == "production":
            secret = self.jwt_secret.get_secret_value() if self.jwt_secret else ""
            if len(secret) < JWT_SECRET_MIN_LENGTH:
                raise ValueError(
                    f"JWT_SECRET must be set with at least {JWT_SECRET_MIN_LENGTH} characters "
                    "when APP_ENV=production"
                )
        if "*" in self.frontend_origin_list:
            raise ValueError("FRONTEND_ORIGINS must list explicit origins, never '*'")
        return self

    @property
    def frontend_origin_list(self) -> list[str]:
        return [o.strip().rstrip("/") for o in self.frontend_origins.split(",") if o.strip()]

    @property
    def jwt_signing_key(self) -> str:
        if self.jwt_secret is not None:
            return self.jwt_secret.get_secret_value()
        return _DEV_JWT_SECRET


def warn_if_insecure(settings: Settings) -> None:
    if settings.jwt_secret is None:
        logger.warning(
            "JWT_SECRET is not set: using an insecure development secret. "
            "Set JWT_SECRET (at least %d characters) outside local development.",
            JWT_SECRET_MIN_LENGTH,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
