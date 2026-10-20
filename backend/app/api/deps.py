import uuid
from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.core.database import get_db

DbSession = Annotated[Session, Depends(get_db)]

# Temporary until authentication lands (T5): the client identifies the analyst by header.
AnalystIdHeader = Annotated[uuid.UUID | None, Header(alias="X-Analyst-Id")]
