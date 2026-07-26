from pydantic import BaseModel, ConfigDict, Field


class AdminDashboardResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    total_requests: int = Field(
        ge=0,
    )

    pending_review: int = Field(
        ge=0,
    )

    approved_not_sent: int = Field(
        ge=0,
    )

    critical_requests: int = Field(
        ge=0,
    )

    status_counts: dict[str, int]
    category_counts: dict[str, int]
    urgency_counts: dict[str, int]