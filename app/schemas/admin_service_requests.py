from pydantic import BaseModel, ConfigDict, Field

from app.schemas.service_request import (
    ServiceRequestRead,
)


class AdminServiceRequestListResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    items: list[ServiceRequestRead]

    total: int = Field(
        ge=0,
    )

    offset: int = Field(
        ge=0,
    )

    limit: int = Field(
        ge=1,
        le=100,
    )