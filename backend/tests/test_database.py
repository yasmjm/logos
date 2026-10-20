from sqlalchemy import text

from app.core.database import build_engine
from tests.settings import TEST_SETTINGS


def test_engine_applies_pool_and_timeouts() -> None:
    settings = TEST_SETTINGS.model_copy(
        update={"db_pool_size": 3, "db_pool_timeout_seconds": 2, "db_statement_timeout_ms": 1234}
    )
    engine = build_engine(settings)
    try:
        assert engine.pool.size() == 3
        assert engine.pool.timeout() == 2
        with engine.connect() as conn:
            assert conn.execute(text("SHOW statement_timeout")).scalar() == "1234ms"
    finally:
        engine.dispose()
