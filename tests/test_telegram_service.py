from unittest.mock import Mock

import httpx
import pytest

from app.services.telegram_service import (
    TelegramAPIError,
    TelegramConfigurationError,
    TelegramService,
)


def test_telegram_service_sends_message() -> None:
    mock_client = Mock(
        spec=httpx.Client
    )

    mock_response = Mock(
        spec=httpx.Response
    )

    mock_response.json.return_value = {
        "ok": True,
        "result": {
            "message_id": 321,
            "chat": {
                "id": 123456789,
            },
            "date": 1700000000,
            "text": "Thank you for your report.",
        },
    }

    mock_client.post.return_value = mock_response

    service = TelegramService(
        token="test-token",
        client=mock_client,
    )

    message_id = service.send_message(
        chat_id=123456789,
        text="Thank you for your report.",
    )

    assert message_id == 321

    mock_client.post.assert_called_once_with(
        (
            "https://api.telegram.org"
            "/bottest-token/sendMessage"
        ),
        json={
            "chat_id": 123456789,
            "text": "Thank you for your report.",
        },
    )

    mock_response.raise_for_status.assert_called_once_with()


def test_telegram_service_removes_outer_whitespace() -> None:
    mock_client = Mock(
        spec=httpx.Client
    )

    mock_response = Mock(
        spec=httpx.Response
    )

    mock_response.json.return_value = {
        "ok": True,
        "result": {
            "message_id": 555,
        },
    }

    mock_client.post.return_value = mock_response

    service = TelegramService(
        token="test-token",
        client=mock_client,
    )

    message_id = service.send_message(
        chat_id=987654321,
        text="   Message with spaces.   ",
    )

    assert message_id == 555

    mock_client.post.assert_called_once_with(
        (
            "https://api.telegram.org"
            "/bottest-token/sendMessage"
        ),
        json={
            "chat_id": 987654321,
            "text": "Message with spaces.",
        },
    )


def test_telegram_service_raises_error_for_http_failure(
) -> None:
    mock_client = Mock(
        spec=httpx.Client
    )

    request = httpx.Request(
        method="POST",
        url=(
            "https://api.telegram.org"
            "/bottest-token/sendMessage"
        ),
    )

    response = httpx.Response(
        status_code=500,
        request=request,
    )

    mock_response = Mock(
        spec=httpx.Response
    )

    mock_response.raise_for_status.side_effect = (
        httpx.HTTPStatusError(
            message="Server error",
            request=request,
            response=response,
        )
    )

    mock_client.post.return_value = mock_response

    service = TelegramService(
        token="test-token",
        client=mock_client,
    )

    with pytest.raises(
        TelegramAPIError,
        match="Telegram message could not be sent",
    ):
        service.send_message(
            chat_id=123456789,
            text="Example message",
        )


def test_telegram_service_raises_error_when_api_rejects_message(
) -> None:
    mock_client = Mock(
        spec=httpx.Client
    )

    mock_response = Mock(
        spec=httpx.Response
    )

    mock_response.json.return_value = {
        "ok": False,
        "error_code": 400,
        "description": "Bad Request: chat not found",
    }

    mock_client.post.return_value = mock_response

    service = TelegramService(
        token="test-token",
        client=mock_client,
    )

    with pytest.raises(
        TelegramAPIError,
        match="Bad Request: chat not found",
    ):
        service.send_message(
            chat_id=123456789,
            text="Example message",
        )


def test_telegram_service_requires_token() -> None:
    with pytest.raises(
        TelegramConfigurationError,
        match="TELEGRAM_BOT_TOKEN is not configured",
    ):
        TelegramService(
            token="",
        )


def test_telegram_service_rejects_empty_message() -> None:
    mock_client = Mock(
        spec=httpx.Client
    )

    service = TelegramService(
        token="test-token",
        client=mock_client,
    )

    with pytest.raises(
        TelegramAPIError,
        match="Telegram message cannot be empty",
    ):
        service.send_message(
            chat_id=123456789,
            text="   ",
        )

    mock_client.post.assert_not_called()