from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ActivityLogRead(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    service_request_id: int
    action: str
    actor_type: str
    actor_id: str | None
    details: dict[str, Any]
    created_at: datetime