from pydantic import BaseModel, ConfigDict, Field


class ServiceRequestApprove(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    approved_response: str | None = Field(
        default=None,
        min_length=10,
        max_length=2000,
    )


class ServiceRequestReject(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    reason: str = Field(
        min_length=3,
        max_length=500,
    )