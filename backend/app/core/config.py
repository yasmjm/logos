from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Logos"
    debug: bool = False
    database_url: str = "postgresql+psycopg://logos:logos@localhost:5433/logos"


@lru_cache
def get_settings() -> Settings:
    return Settings()
