from pydantic import BaseModel, ConfigDict, Field


class ServiceRequestApprove(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    admin_id: str = Field(
        min_length=1,
        max_length=100,
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

    admin_id: str = Field(
        min_length=1,
        max_length=100,
    )

    reason: str = Field(
        min_length=3,
        max_length=500,
    )