from typing import Any

from pydantic import BaseModel, Field

from app.schemas.incident import AnalystRef, IncidentDetail


class ProblemDetail(BaseModel):
    """RFC 9457 problem details, returned as application/problem+json."""

    type: str = Field(default="about:blank", examples=["about:blank"])
    title: str = Field(examples=["Not Found"])
    status: int = Field(examples=[404])
    detail: str = Field(examples=["Incident 3f0c... not found."])


class ServerProblemDetail(ProblemDetail):
    """500 and 503: include the request ID so support can find the logs."""

    title: str = Field(examples=["Service Unavailable"])
    status: int = Field(examples=[503])
    detail: str = Field(
        examples=["The database is temporarily unavailable. Please try again shortly."]
    )
    request_id: str | None = Field(default=None, examples=["9f1c2e7a4b3d4e5f8a6b7c8d9e0f1a2b"])


class InvalidParam(BaseModel):
    location: str = Field(examples=["query parameter 'severity'"])
    message: str = Field(examples=["Input should be 'high', 'medium' or 'low'"])
    input: Any = Field(default=None, examples=["urgent"])


class ValidationProblemDetail(ProblemDetail):
    title: str = Field(examples=["Unprocessable Entity"])
    status: int = Field(examples=[422])
    detail: str = Field(
        examples=[
            "Invalid query parameter 'severity': Input should be 'high', 'medium' or 'low' "
            "(got 'urgent')"
        ]
    )
    errors: list[InvalidParam]


class NotResponsibleProblemDetail(ProblemDetail):
    title: str = Field(examples=["Forbidden"])
    status: int = Field(examples=[403])
    detail: str = Field(
        examples=["Only the analyst responsible for this incident (Ana Souza) can change it."]
    )
    assignee: AnalystRef | None


class ConflictProblemDetail(ProblemDetail):
    """409: the client's version is outdated. "current" is the incident as it is now."""

    title: str = Field(examples=["Conflict"])
    status: int = Field(examples=[409])
    detail: str = Field(
        examples=["Incident was changed by someone else: version 2 is outdated (current: 3)."]
    )
    current: IncidentDetail
