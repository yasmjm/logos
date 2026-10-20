import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, make_url, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.main import app
from app.models import Analyst, Base
from tests.factories import auth_headers, make_analyst
from tests.settings import TEST_SETTINGS

TEST_DATABASE_NAME = "logos_test"


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
def anon_client(db: Session) -> Generator[TestClient, None, None]:
    """Client without credentials."""
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_settings] = lambda: TEST_SETTINGS
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def current_analyst(db: Session) -> Analyst:
    return make_analyst(db, "tester", "Analista de Teste")


@pytest.fixture
def client(anon_client: TestClient, current_analyst: Analyst) -> TestClient:
    """Client logged in as current_analyst (pass headers=auth_headers(x) to act as x)."""
    anon_client.headers.update(auth_headers(current_analyst))
    return anon_client
