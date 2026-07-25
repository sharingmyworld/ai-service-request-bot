from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.service_request import ServiceRequestStatus


class ServiceRequestCreate(BaseModel):
    telegram_chat_id: int

    telegram_user_id: int | None = None

    user_message: str = Field(
        min_length=3,
        max_length=4000,
    )


class ServiceRequestRead(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    telegram_chat_id: int
    telegram_user_id: int | None
    telegram_update_id: int | None
    user_message: str
    category: str | None
    urgency: str | None
    location: str | None
    status: ServiceRequestStatus
    draft_response: str | None
    approved_response: str | None
    created_at: datetime
    updated_at: datetime