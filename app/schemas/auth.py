from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AccessTokenResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    access_token: str
    token_type: Literal["bearer"] = "bearer"


class PasswordChangeRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    current_password: str = Field(
        min_length=1,
        max_length=128,
    )

    new_password: str = Field(
        min_length=12,
        max_length=128,
    )


class PasswordChangeResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    message: str