from typing import Literal

from pydantic import BaseModel, ConfigDict


class AccessTokenResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    access_token: str
    token_type: Literal["bearer"] = "bearer"