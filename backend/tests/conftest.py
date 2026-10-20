import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, make_url, text
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.main import app
from app.models import Base

TEST_DATABASE_NAME = "logos_test"
TEST_INGEST_API_KEY = "test-ingest-key"


def _test_database_url() -> str:
    if url := os.getenv("TEST_DATABASE_URL"):
        return url
    return (
        make_url(get_settings().database_url)
        .set(database=TEST_DATABASE_NAME)
        .render_as_string(hide_password=False)
    )


@pytest.fixture(scope="session")
def db_engine() -> Generator[Engine, None, None]:
    url = make_url(_test_database_url())

    # Create the test database on first use (same Postgres container as dev).
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        exists = conn.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": url.database}
        )
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{url.database}"'))
    admin.dispose()

    engine = create_engine(url)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db(db_engine: Engine) -> Generator[Session, None, None]:
    """Session bound to an outer transaction that is rolled back after each test."""
    connection = db_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db: Session) -> Generator[TestClient, None, None]:
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_settings] = lambda: Settings(ingest_api_key=TEST_INGEST_API_KEY)
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
