from unittest.mock import Mock

from fastapi.testclient import TestClient

from app.main import app
from app.models.service_request import (
    ServiceRequest,
    ServiceRequestStatus,
)
from app.routers.service_requests import (
    provide_telegram_service,
)
from app.services.telegram_service import (
    TelegramAPIError,
    TelegramService,
)


APPROVED_RESPONSE = (
    "Thank you for your report. "
    "The maintenance team will review the issue."
)


def create_approved_service_request(
    client: TestClient,
    database_session,
) -> int:
    service_request = ServiceRequest(
        telegram_chat_id=123456789,
        telegram_user_id=987654321,
        user_message=(
            "Water is leaking under the kitchen sink."
        ),
        category="plumbing",
        urgency="high",
        location="Kitchen",
        status=ServiceRequestStatus.APPROVED,
        draft_response=APPROVED_RESPONSE,
        approved_response=APPROVED_RESPONSE,
    )

    database_session.add(service_request)
    database_session.commit()
    database_session.refresh(service_request)

    return service_request.id


def test_send_approved_response_uses_telegram_service(
    client: TestClient,
    database_session,
) -> None:
    request_id = create_approved_service_request(
        client,
        database_session,
    )

    mock_telegram_service = Mock(
        spec=TelegramService
    )

    mock_telegram_service.send_message.return_value = 456

    app.dependency_overrides[
        provide_telegram_service
    ] = lambda: mock_telegram_service

    response = client.post(
        f"/service-requests/{request_id}/send"
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["id"] == request_id
    assert response_data["status"] == "sent"
    assert response_data["approved_response"] == (
        APPROVED_RESPONSE
    )

    mock_telegram_service.send_message.assert_called_once_with(
        chat_id=123456789,
        text=APPROVED_RESPONSE,
    )

    activity_response = client.get(
        f"/service-requests/{request_id}/activity-logs"
    )

    assert activity_response.status_code == 200

    activity_logs = activity_response.json()

    assert len(activity_logs) == 1

    delivery_log = activity_logs[0]

    assert delivery_log["action"] == (
        "telegram_message_sent"
    )
    assert delivery_log["actor_type"] == "telegram_bot"
    assert delivery_log["actor_id"] is None
    assert delivery_log["details"] == {
        "telegram_chat_id": 123456789,
        "telegram_message_id": 456,
    }


def test_send_response_returns_409_when_not_approved(
    client: TestClient,
) -> None:
    create_response = client.post(
        "/service-requests",
        json={
            "telegram_chat_id": 111222333,
            "telegram_user_id": 444555666,
            "user_message": (
                "The heating is not working."
            ),
        },
    )

    assert create_response.status_code == 201

    request_id = create_response.json()["id"]

    mock_telegram_service = Mock(
        spec=TelegramService
    )

    app.dependency_overrides[
        provide_telegram_service
    ] = lambda: mock_telegram_service

    response = client.post(
        f"/service-requests/{request_id}/send"
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": (
            "Only approved service requests "
            "can be sent"
        )
    }

    mock_telegram_service.send_message.assert_not_called()


def test_send_response_returns_404_when_request_missing(
    client: TestClient,
) -> None:
    mock_telegram_service = Mock(
        spec=TelegramService
    )

    app.dependency_overrides[
        provide_telegram_service
    ] = lambda: mock_telegram_service

    response = client.post(
        "/service-requests/999999999/send"
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Service request not found"
    }

    mock_telegram_service.send_message.assert_not_called()


def test_send_response_returns_503_when_telegram_fails(
    client: TestClient,
    database_session,
) -> None:
    request_id = create_approved_service_request(
        client,
        database_session,
    )

    mock_telegram_service = Mock(
        spec=TelegramService
    )

    mock_telegram_service.send_message.side_effect = (
        TelegramAPIError(
            "Telegram message could not be sent"
        )
    )

    app.dependency_overrides[
        provide_telegram_service
    ] = lambda: mock_telegram_service

    response = client.post(
        f"/service-requests/{request_id}/send"
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Telegram message could not be sent"
    }

    request_response = client.get(
        f"/service-requests/{request_id}"
    )

    assert request_response.status_code == 200
    assert request_response.json()["status"] == "approved"

    activity_response = client.get(
        f"/service-requests/{request_id}/activity-logs"
    )

    assert activity_response.status_code == 200
    assert activity_response.json() == []


def test_sent_response_cannot_be_sent_again(
    client: TestClient,
    database_session,
) -> None:
    request_id = create_approved_service_request(
        client,
        database_session,
    )

    mock_telegram_service = Mock(
        spec=TelegramService
    )

    mock_telegram_service.send_message.return_value = 789

    app.dependency_overrides[
        provide_telegram_service
    ] = lambda: mock_telegram_service

    first_response = client.post(
        f"/service-requests/{request_id}/send"
    )

    assert first_response.status_code == 200
    assert first_response.json()["status"] == "sent"

    second_response = client.post(
        f"/service-requests/{request_id}/send"
    )

    assert second_response.status_code == 409
    assert second_response.json() == {
        "detail": (
            "Only approved service requests "
            "can be sent"
        )
    }

    mock_telegram_service.send_message.assert_called_once()