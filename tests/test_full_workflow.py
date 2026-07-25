from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.routers.service_requests import (
    provide_telegram_service,
)
from app.routers.telegram_webhook import (
    get_configured_telegram_webhook_secret,
)
from app.schemas.ai_analysis import (
    AIServiceRequestAnalysis,
    ProblemCategory,
    UrgencyLevel,
)
from app.services.openai_service import OpenAIService
from app.services.telegram_service import TelegramService


USER_MESSAGE = (
    "Water is leaking under the kitchen sink "
    "in apartment 12."
)

AI_DRAFT_RESPONSE = (
    "Thank you for reporting the leak. "
    "The maintenance team will review your request."
)


def test_complete_service_request_workflow(
    client: TestClient,
    admin_auth: dict,
) -> None:
    app.dependency_overrides[
        get_configured_telegram_webhook_secret
    ] = lambda: "test-webhook-secret"

    mock_ai_service = Mock(
        spec=OpenAIService
    )

    mock_ai_service.analyze_service_request.return_value = (
        AIServiceRequestAnalysis(
            category=ProblemCategory.PLUMBING,
            urgency=UrgencyLevel.HIGH,
            location="Kitchen, apartment 12",
            summary=(
                "Water is leaking under "
                "the kitchen sink."
            ),
            draft_response=AI_DRAFT_RESPONSE,
        )
    )

    mock_telegram_service = Mock(
        spec=TelegramService
    )

    mock_telegram_service.send_message.return_value = 9001

    app.dependency_overrides[
        provide_telegram_service
    ] = lambda: mock_telegram_service

    telegram_update = {
        "update_id": 5001,
        "message": {
            "message_id": 101,
            "from": {
                "id": 987654321,
                "is_bot": False,
                "first_name": "Test User",
            },
            "chat": {
                "id": 123456789,
                "type": "private",
            },
            "text": USER_MESSAGE,
        },
    }

    with patch(
        (
            "app.routers.telegram_webhook"
            ".get_openai_service"
        ),
        return_value=mock_ai_service,
    ):
        webhook_response = client.post(
            "/telegram/webhook",
            headers={
                "X-Telegram-Bot-Api-Secret-Token": (
                    "test-webhook-secret"
                ),
            },
            json=telegram_update,
        )

    assert webhook_response.status_code == 200
    assert webhook_response.json()["status"] == "accepted"

    request_id = webhook_response.json()[
        "service_request_id"
    ]

    assert request_id > 0

    drafted_response = client.get(
        f"/service-requests/{request_id}"
    )

    assert drafted_response.status_code == 200

    drafted_request = drafted_response.json()

    assert drafted_request["status"] == "drafted"
    assert drafted_request["telegram_update_id"] == 5001
    assert drafted_request["category"] == "plumbing"
    assert drafted_request["urgency"] == "high"
    assert drafted_request["location"] == (
        "Kitchen, apartment 12"
    )
    assert drafted_request["draft_response"] == (
        AI_DRAFT_RESPONSE
    )
    assert drafted_request["approved_response"] is None

    approval_response = client.post(
        f"/service-requests/{request_id}/approve",
        headers=admin_auth["headers"],
        json={},
    )

    assert approval_response.status_code == 200

    approved_request = approval_response.json()

    assert approved_request["status"] == "approved"
    assert approved_request["approved_response"] == (
        AI_DRAFT_RESPONSE
    )

    send_response = client.post(
        f"/service-requests/{request_id}/send",
        headers=admin_auth["headers"],
    )

    assert send_response.status_code == 200

    sent_request = send_response.json()

    assert sent_request["status"] == "sent"
    assert sent_request["approved_response"] == (
        AI_DRAFT_RESPONSE
    )

    mock_ai_service.analyze_service_request.assert_called_once_with(
        USER_MESSAGE
    )

    mock_telegram_service.send_message.assert_called_once_with(
        chat_id=123456789,
        text=AI_DRAFT_RESPONSE,
    )

    activity_response = client.get(
        f"/service-requests/{request_id}/activity-logs"
    )

    assert activity_response.status_code == 200

    activity_logs = activity_response.json()

    actions = [
        activity_log["action"]
        for activity_log in activity_logs
    ]

    assert actions == [
        "service_request_created",
        "ai_analysis_completed",
        "service_request_approved",
        "telegram_message_sent",
    ]

    approval_log = activity_logs[2]

    assert approval_log["actor_type"] == "admin"
    assert approval_log["actor_id"] == str(
        admin_auth["admin_id"]
    )
    assert approval_log["details"] == {
        "admin_username": admin_auth["username"],
        "response_edited": False,
    }

    delivery_log = activity_logs[3]

    assert delivery_log["actor_type"] == "admin"
    assert delivery_log["actor_id"] == str(
        admin_auth["admin_id"]
    )
    assert delivery_log["details"] == {
        "admin_username": admin_auth["username"],
        "telegram_chat_id": 123456789,
        "telegram_message_id": 9001,
    }