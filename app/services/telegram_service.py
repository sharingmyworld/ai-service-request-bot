import httpx
from pydantic import BaseModel, ConfigDict, ValidationError

from app.config import settings


class TelegramConfigurationError(RuntimeError):
    """Raised when Telegram configuration is missing."""


class TelegramAPIError(RuntimeError):
    """Raised when a Telegram API request fails."""


class TelegramMessageResult(BaseModel):
    model_config = ConfigDict(
        extra="ignore",
    )

    message_id: int


class TelegramSendMessageResponse(BaseModel):
    model_config = ConfigDict(
        extra="ignore",
    )

    ok: bool
    result: TelegramMessageResult | None = None
    description: str | None = None


class TelegramService:
    def __init__(
        self,
        token: str | None = None,
        client: httpx.Client | None = None,
        base_url: str = "https://api.telegram.org",
    ) -> None:
        resolved_token = (
            token
            if token is not None
            else settings.telegram_bot_token
        )

        if not resolved_token or not resolved_token.strip():
            raise TelegramConfigurationError(
                "TELEGRAM_BOT_TOKEN is not configured"
            )

        self.token = resolved_token.strip()

        self.send_message_url = (
            f"{base_url.rstrip('/')}"
            f"/bot{self.token}/sendMessage"
        )

        self.client = client or httpx.Client(
            timeout=10.0,
        )

    def send_message(
        self,
        chat_id: int,
        text: str,
    ) -> int:
        cleaned_text = text.strip()

        if not cleaned_text:
            raise TelegramAPIError(
                "Telegram message cannot be empty"
            )

        try:
            response = self.client.post(
                self.send_message_url,
                json={
                    "chat_id": chat_id,
                    "text": cleaned_text,
                },
            )

            response.raise_for_status()

            telegram_response = (
                TelegramSendMessageResponse.model_validate(
                    response.json()
                )
            )

        except (
            httpx.HTTPError,
            ValidationError,
            ValueError,
        ) as error:
            raise TelegramAPIError(
                "Telegram message could not be sent"
            ) from error

        if (
            not telegram_response.ok
            or telegram_response.result is None
        ):
            error_description = (
                telegram_response.description
                or "Telegram API rejected the message"
            )

            raise TelegramAPIError(
                error_description
            )

        return telegram_response.result.message_id