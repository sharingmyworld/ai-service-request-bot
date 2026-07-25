from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TelegramUser(BaseModel):
    model_config = ConfigDict(
        extra="ignore",
    )

    id: int
    is_bot: bool = False
    first_name: str | None = None
    username: str | None = None


class TelegramChat(BaseModel):
    model_config = ConfigDict(
        extra="ignore",
    )

    id: int
    type: str


class TelegramMessage(BaseModel):
    model_config = ConfigDict(
        extra="ignore",
        populate_by_name=True,
    )

    message_id: int

    sender: TelegramUser | None = Field(
        default=None,
        alias="from",
    )

    chat: TelegramChat

    text: str | None = Field(
        default=None,
        max_length=4000,
    )


class TelegramUpdate(BaseModel):
    model_config = ConfigDict(
        extra="ignore",
    )

    update_id: int
    message: TelegramMessage | None = None


class TelegramWebhookResponse(BaseModel):
    status: Literal[
        "accepted",
        "ignored",
        "duplicate",
    ]

    service_request_id: int | None = None