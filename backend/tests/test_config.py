import pytest
from sqlalchemy import make_url

from app.core.config import Settings

NEON = (
    "postgresql://user:p%40ss@ep-cool-name-123.us-east-1.aws.neon.tech/logos"
    "?sslmode=require&channel_binding=require"
)


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        (NEON, NEON.replace("postgresql://", "postgresql+psycopg://", 1)),
        ("postgres://u:p@host:5432/db", "postgresql+psycopg://u:p@host:5432/db"),
        ("postgresql+psycopg://u:p@host/db", "postgresql+psycopg://u:p@host/db"),
    ],
)
def test_database_url_uses_psycopg_driver(given: str, expected: str) -> None:
    assert Settings(_env_file=None, database_url=given).database_url == expected


def test_neon_url_keeps_ssl_parameters_for_psycopg() -> None:
    url = make_url(Settings(_env_file=None, database_url=NEON).database_url)

    assert url.drivername == "postgresql+psycopg"
    assert url.password == "p@ss"
    assert url.query == {"sslmode": "require", "channel_binding": "require"}


def test_invalid_configuration_error_never_echoes_values(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import ConfigurationError, get_settings

    secret_url = "postgresql://user:super-secret-password@db.example.com/logos"
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", secret_url)
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.chdir("/")  # no .env file
    get_settings.cache_clear()
    try:
        with pytest.raises(ConfigurationError) as raised:
            get_settings()
    finally:
        get_settings.cache_clear()

    message = str(raised.value)
    assert "JWT_SECRET must be set" in message
    assert "super-secret-password" not in message
    assert "db.example.com" not in message
    assert raised.value.__cause__ is None
    assert raised.value.__suppress_context__
