from pydantic import BaseModel, Field


class IncidentMetrics(BaseModel):
    window_hours: int = Field(default=24, description="Window for MTTA and MTTR.")
    mtta_seconds: float | None = Field(
        description="Mean time to acknowledge (created → assumed), incidents assumed in the window."
    )
    mtta_count: int = Field(description="Incidents used in the MTTA average.")
    mttr_seconds: float | None = Field(
        description="Mean time to resolve (created → closed/inconclusive), resolved in the window."
    )
    mttr_count: int = Field(description="Incidents used in the MTTR average.")
    escalated_now: int = Field(description="High, open and without owner for more than 5 minutes.")
    sla_breached_now: int = Field(description="Open, without owner, past their severity's SLA.")
