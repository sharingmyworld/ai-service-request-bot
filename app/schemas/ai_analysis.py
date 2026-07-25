from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ProblemCategory(StrEnum):
    PLUMBING = "plumbing"
    ELECTRICAL = "electrical"
    HEATING = "heating"
    ELEVATOR = "elevator"
    SECURITY = "security"
    CLEANING = "cleaning"
    OTHER = "other"


class UrgencyLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AIServiceRequestAnalysis(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    category: ProblemCategory

    urgency: UrgencyLevel

    location: str | None = Field(
        default=None,
        min_length=2,
        max_length=255,
    )

    summary: str = Field(
        min_length=5,
        max_length=500,
    )

    draft_response: str = Field(
        min_length=10,
        max_length=2000,
    )