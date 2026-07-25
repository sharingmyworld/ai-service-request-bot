from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AdminUserRead(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    username: str
    is_active: bool
    created_at: datetime