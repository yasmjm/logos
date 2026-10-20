from app.core.config import Settings

TEST_INGEST_API_KEY = "test-ingest-key"
# _env_file=None: tests never read the developer's .env.
TEST_SETTINGS = Settings(
    _env_file=None,
    app_env="test",
    ingest_api_key=TEST_INGEST_API_KEY,
    jwt_secret="test-jwt-secret-with-at-least-32-characters",
)
