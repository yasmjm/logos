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
