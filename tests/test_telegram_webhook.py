from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.routers.telegram_webhook import (
    get_configured_telegram_webhook_secret,
)
from app.schemas.ai_analysis import (
    AIServiceRequestAnalysis,
    ProblemCategory,
    UrgencyLevel,
)
from app.services.openai_service import (
    AIAnalysisError,
    OpenAIService,
)


WEBHOOK_HEADERS = {
    "X-Telegram-Bot-Api-Secret-Token": (
        "test-webhook-secret"
    ),
}


def configure_test_webhook_secret() -> None:
    app.dependency_overrides[
        get_configured_telegram_webhook_secret
    ] = lambda: "test-webhook-secret"


def create_mock_ai_service() -> Mock:
    mock_ai_service = Mock(
        spec=OpenAIService
    )

    mock_ai_service.analyze_service_request.return_value = (
        AIServiceRequestAnalysis(
            category=ProblemCategory.PLUMBING,
            urgency=UrgencyLevel.HIGH,
            location="Bathroom",
            summary=(
                "Water is leaking under "
                "the bathroom sink."
            ),
            draft_response=(
                "Thank you for reporting the leak. "
                "The maintenance team will review "
                "your request."
            ),
        )
    )

    return mock_ai_service


def create_telegram_update(
    update_id: int,
) -> dict:
    return {
        "update_id": update_id,
        "message": {
            "message_id": 77,
            "from": {
                "id": 987654321,
                "is_bot": False,
                "first_name": "Test User",
                "username": "test_user",
            },
            "chat": {
                "id": 123456789,
                "type": "private",
            },
            "date": 1700000000,
            "text": (
                "Water is leaking under "
                "the bathroom sink."
            ),
        },
    }


def test_telegram_webhook_creates_and_analyzes_request(
    client: TestClient,
) -> None:
    configure_test_webhook_secret()

    user_message = (
        "Water is leaking under the bathroom sink."
    )

    mock_ai_service = create_mock_ai_service()

    with patch(
        (
            "app.routers.telegram_webhook"
            ".get_openai_service"
        ),
        return_value=mock_ai_service,
    ):
        response = client.post(
            "/telegram/webhook",
            headers=WEBHOOK_HEADERS,
            json=create_telegram_update(
                update_id=1001
            ),
        )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["status"] == "accepted"
    assert response_data["service_request_id"] > 0

    request_id = response_data["service_request_id"]

    mock_ai_service.analyze_service_request.assert_called_once_with(
        user_message
    )

    request_response = client.get(
        f"/service-requests/{request_id}"
    )

    assert request_response.status_code == 200

    saved_request = request_response.json()

    assert saved_request["telegram_chat_id"] == 123456789
    assert saved_request["telegram_user_id"] == 987654321
    assert saved_request["telegram_update_id"] == 1001
    assert saved_request["user_message"] == user_message
    assert saved_request["category"] == "plumbing"
    assert saved_request["urgency"] == "high"
    assert saved_request["location"] == "Bathroom"
    assert saved_request["status"] == "drafted"
    assert saved_request["draft_response"] == (
        "Thank you for reporting the leak. "
        "The maintenance team will review "
        "your request."
    )
    assert saved_request["approved_response"] is None

    activity_response = client.get(
        f"/service-requests/{request_id}/activity-logs"
    )

    assert activity_response.status_code == 200

    activity_logs = activity_response.json()

    assert len(activity_logs) == 2

    assert activity_logs[0]["action"] == (
        "service_request_created"
    )
    assert activity_logs[1]["action"] == (
        "ai_analysis_completed"
    )


def test_telegram_webhook_ignores_duplicate_update(
    client: TestClient,
) -> None:
    configure_test_webhook_secret()

    mock_ai_service = create_mock_ai_service()

    telegram_update = create_telegram_update(
        update_id=2001
    )

    with patch(
        (
            "app.routers.telegram_webhook"
            ".get_openai_service"
        ),
        return_value=mock_ai_service,
    ):
        first_response = client.post(
            "/telegram/webhook",
            headers=WEBHOOK_HEADERS,
            json=telegram_update,
        )

        second_response = client.post(
            "/telegram/webhook",
            headers=WEBHOOK_HEADERS,
            json=telegram_update,
        )

    assert first_response.status_code == 200
    assert first_response.json()["status"] == "accepted"

    assert second_response.status_code == 200
    assert second_response.json()["status"] == "duplicate"

    first_request_id = (
        first_response.json()["service_request_id"]
    )

    second_request_id = (
        second_response.json()["service_request_id"]
    )

    assert second_request_id == first_request_id

    mock_ai_service.analyze_service_request.assert_called_once()

    requests_response = client.get(
        "/service-requests"
    )

    assert requests_response.status_code == 200

    matching_requests = [
        service_request
        for service_request in requests_response.json()
        if service_request["telegram_update_id"] == 2001
    ]

    assert len(matching_requests) == 1

    activity_response = client.get(
        (
            f"/service-requests/{first_request_id}"
            "/activity-logs"
        )
    )

    assert activity_response.status_code == 200

    activity_logs = activity_response.json()

    assert len(activity_logs) == 3
    assert activity_logs[-1]["action"] == (
        "telegram_update_duplicate_ignored"
    )
    assert activity_logs[-1]["actor_type"] == "telegram"
    assert activity_logs[-1]["details"] == {
        "telegram_update_id": 2001,
    }


def test_telegram_webhook_saves_request_when_ai_fails(
    client: TestClient,
) -> None:
    configure_test_webhook_secret()

    user_message = (
        "The heating is not working in apartment 8."
    )

    mock_ai_service = Mock(
        spec=OpenAIService
    )

    mock_ai_service.analyze_service_request.side_effect = (
        AIAnalysisError(
            "OpenAI did not return a valid analysis"
        )
    )

    with patch(
        (
            "app.routers.telegram_webhook"
            ".get_openai_service"
        ),
        return_value=mock_ai_service,
    ):
        response = client.post(
            "/telegram/webhook",
            headers=WEBHOOK_HEADERS,
            json={
                "update_id": 1002,
                "message": {
                    "message_id": 78,
                    "from": {
                        "id": 987654321,
                        "is_bot": False,
                        "first_name": "Test User",
                    },
                    "chat": {
                        "id": 123456789,
                        "type": "private",
                    },
                    "text": user_message,
                },
            },
        )

    assert response.status_code == 200
    assert response.json()["status"] == "accepted"

    request_id = response.json()["service_request_id"]

    request_response = client.get(
        f"/service-requests/{request_id}"
    )

    assert request_response.status_code == 200

    saved_request = request_response.json()

    assert saved_request["telegram_update_id"] == 1002
    assert saved_request["status"] == "new"
    assert saved_request["category"] is None
    assert saved_request["urgency"] is None
    assert saved_request["location"] is None
    assert saved_request["draft_response"] is None

    activity_response = client.get(
        f"/service-requests/{request_id}/activity-logs"
    )

    assert activity_response.status_code == 200

    activity_logs = activity_response.json()

    assert len(activity_logs) == 2
    assert activity_logs[0]["action"] == (
        "service_request_created"
    )
    assert activity_logs[1]["action"] == (
        "ai_analysis_failed"
    )
    assert activity_logs[1]["details"] == {
        "error_type": "AIAnalysisError",
    }


def test_telegram_webhook_rejects_invalid_secret(
    client: TestClient,
) -> None:
    configure_test_webhook_secret()

    with patch(
        (
            "app.routers.telegram_webhook"
            ".get_openai_service"
        )
    ) as mock_service_factory:
        response = client.post(
            "/telegram/webhook",
            headers={
                "X-Telegram-Bot-Api-Secret-Token": (
                    "wrong-secret"
                ),
            },
            json=create_telegram_update(
                update_id=1003
            ),
        )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid Telegram webhook secret"
    }

    mock_service_factory.assert_not_called()


def test_telegram_webhook_ignores_non_text_update(
    client: TestClient,
) -> None:
    configure_test_webhook_secret()

    with patch(
        (
            "app.routers.telegram_webhook"
            ".get_openai_service"
        )
    ) as mock_service_factory:
        response = client.post(
            "/telegram/webhook",
            headers=WEBHOOK_HEADERS,
            json={
                "update_id": 1004,
                "message": {
                    "message_id": 80,
                    "from": {
                        "id": 987654321,
                        "is_bot": False,
                        "first_name": "Test User",
                    },
                    "chat": {
                        "id": 123456789,
                        "type": "private",
                    },
                    "photo": [
                        {
                            "file_id": "example-file-id",
                            "file_unique_id": (
                                "example-unique-id"
                            ),
                            "width": 100,
                            "height": 100,
                        }
                    ],
                },
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "status": "ignored",
        "service_request_id": None,
    }

    mock_service_factory.assert_not_called()