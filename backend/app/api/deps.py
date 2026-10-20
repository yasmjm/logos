import hashlib
import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.rate_limit import INGEST_LIMITER, LOGIN_LIMITER, RateLimiter
from app.core.retry import read_with_retry
from app.core.tokens import ExpiredToken, InvalidToken, decode_access_token
from app.models import Analyst

DbSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]

_api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,
    description="Ingestion key shared with trucks and integrations (INGEST_API_KEY).",
)

# tokenUrl makes Swagger's Authorize button log in with username and password.
_oauth2 = OAuth2PasswordBearer(
    tokenUrl="/auth/login",
    auto_error=False,
    description="Analyst login. In Swagger, use Authorize with username and password.",
)


def require_ingest_key(
    api_key: Annotated[str | None, Security(_api_key_header)], settings: AppSettings
) -> str:
    expected = settings.ingest_api_key
    # Fail closed: with no key configured, nobody can ingest.
    if (
        api_key is None
        or expected is None
        or not secrets.compare_digest(api_key.encode(), expected.get_secret_value().encode())
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing or invalid API key.")
    return api_key


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status.HTTP_401_UNAUTHORIZED, detail, headers={"WWW-Authenticate": "Bearer"}
    )


def get_current_analyst(
    token: Annotated[str | None, Security(_oauth2)], db: DbSession, settings: AppSettings
) -> Analyst:
    if token is None:
        raise _unauthorized("Not authenticated. Log in at POST /auth/login.")
    try:
        analyst_id = decode_access_token(token, settings)
    except ExpiredToken:
        raise _unauthorized("Session expired. Log in again.") from None
    except InvalidToken:
        raise _unauthorized("Invalid access token.") from None

    analyst = read_with_retry(db, lambda: db.get(Analyst, analyst_id))
    if analyst is None:  # e.g. the account was removed after the token was issued
        raise _unauthorized("Invalid access token.")
    return analyst


CurrentAnalyst = Annotated[Analyst, Depends(get_current_analyst)]


def _enforce(limiter: RateLimiter, key: str) -> None:
    retry_after = limiter.hit(key)
    if retry_after is not None:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Too many requests. Try again in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)},
        )


def limit_login_attempts(request: Request) -> None:
    # Per client IP. Behind a proxy this needs uvicorn --proxy-headers (docs/adr/0001).
    client_ip = request.client.host if request.client else "unknown"
    _enforce(LOGIN_LIMITER, f"login:{client_ip}")


def limit_ingestion(api_key: Annotated[str, Depends(require_ingest_key)]) -> None:
    # Per key, counted only after the key is validated; never keep the raw key around.
    _enforce(INGEST_LIMITER, hashlib.sha256(api_key.encode()).hexdigest())
