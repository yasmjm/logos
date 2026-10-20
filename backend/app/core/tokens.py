import uuid
from datetime import UTC, datetime, timedelta

import jwt

from app.core.config import Settings

ALGORITHM = "HS256"


class InvalidToken(Exception):
    pass


class ExpiredToken(InvalidToken):
    pass


def create_access_token(analyst_id: uuid.UUID, settings: Settings) -> str:
    now = datetime.now(UTC)
    claims = {
        "sub": str(analyst_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expires_minutes),
    }
    return jwt.encode(claims, settings.jwt_signing_key, algorithm=ALGORITHM)


def decode_access_token(token: str, settings: Settings) -> uuid.UUID:
    try:
        claims = jwt.decode(
            token,
            settings.jwt_signing_key,
            algorithms=[ALGORITHM],  # pinned: never trust the token's own "alg"
            options={"require": ["sub", "exp", "iat"]},
        )
        return uuid.UUID(claims["sub"])
    except jwt.ExpiredSignatureError as exc:
        raise ExpiredToken from exc
    except (jwt.InvalidTokenError, ValueError) as exc:
        raise InvalidToken from exc
