import secrets
import uuid
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.models import Analyst

DbSession = Annotated[Session, Depends(get_db)]

# Temporary until authentication lands (T5): the client identifies the analyst by header.
AnalystIdHeader = Annotated[uuid.UUID | None, Header(alias="X-Analyst-Id")]
RequiredAnalystIdHeader = Annotated[uuid.UUID, Header(alias="X-Analyst-Id")]

_api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,
    description="Ingestion key shared with trucks and integrations (INGEST_API_KEY).",
)


def require_ingest_key(
    api_key: Annotated[str | None, Security(_api_key_header)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    expected = settings.ingest_api_key
    # Fail closed: with no key configured, nobody can ingest.
    if (
        api_key is None
        or expected is None
        or not secrets.compare_digest(api_key.encode(), expected.get_secret_value().encode())
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing or invalid API key.")


def require_existing_analyst(analyst_id: RequiredAnalystIdHeader, db: DbSession) -> uuid.UUID:
    if db.get(Analyst, analyst_id) is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, f"Unknown analyst {analyst_id} in X-Analyst-Id."
        )
    return analyst_id


# The acting analyst, validated against the database (temporary until T5).
ActingAnalystId = Annotated[uuid.UUID, Depends(require_existing_analyst)]
