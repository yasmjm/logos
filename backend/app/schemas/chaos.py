from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class ChaosConfig(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"examples": [{"latency_ms": 800, "failure_rate": 0.3}]},
    )

    latency_ms: Annotated[int, Field(ge=0, le=5000, description="Added to each /incidents call.")]
    failure_rate: Annotated[
        float, Field(ge=0, le=1, description="Share of /incidents calls answered with 503.")
    ]


class ChaosStatus(BaseModel):
    latency_ms: int
    failure_rate: float
    active: bool
    expires_at: datetime | None = Field(description="Chaos turns itself off at this moment.")
