from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Logos"
    debug: bool = False
    database_url: str = "postgresql+psycopg://logos:logos@localhost:5433/logos"
    # Shared secret for POST /incidents. When unset, ingestion rejects every request.
    ingest_api_key: SecretStr | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
