from unittest.mock import Mock

from fastapi.testclient import TestClient

from app.main import app
from app.routers.service_requests import (
    provide_openai_service,
)
from app.schemas.ai_analysis import (
    AIServiceRequestAnalysis,
    ProblemCategory,
    UrgencyLevel,
)
from app.services.openai_service import OpenAIService


AI_DRAFT_RESPONSE = (
    "Thank you for reporting the electrical problem. "
    "The maintenance team will review your request."
)


def create_drafted_service_request(
    client: TestClient,
) -> int:
    user_message = (
        "There are sparks near the electrical panel "
        "in the basement."
    )

    create_response = client.post(
        "/service-requests",
        json={
            "telegram_chat_id": 123456789,
            "telegram_user_id": 987654321,
            "user_message": user_message,
        },
    )

    assert create_response.status_code == 201

    request_id = create_response.json()["id"]

    mock_ai_service = Mock(
        spec=OpenAIService
    )

    mock_ai_service.analyze_service_request.return_value = (
        AIServiceRequestAnalysis(
            category=ProblemCategory.ELECTRICAL,
            urgency=UrgencyLevel.CRITICAL,
            location="Basement",
            summary=(
                "Sparks are visible near "
                "the electrical panel."
            ),
            draft_response=AI_DRAFT_RESPONSE,
        )
    )

    app.dependency_overrides[
        provide_openai_service
    ] = lambda: mock_ai_service

    analyze_response = client.post(
        f"/service-requests/{request_id}/analyze"
    )

    assert analyze_response.status_code == 200
    assert analyze_response.json()["status"] == "drafted"

    return request_id


def test_approve_service_request_uses_ai_draft(
    client: TestClient,
    admin_auth: dict,
) -> None:
    request_id = create_drafted_service_request(client)

    response = client.post(
        f"/service-requests/{request_id}/approve",
        headers=admin_auth["headers"],
        json={},
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["status"] == "approved"
    assert response_data["approved_response"] == (
        AI_DRAFT_RESPONSE
    )

    activity_response = client.get(
        f"/service-requests/{request_id}/activity-logs"
    )

    assert activity_response.status_code == 200

    activity_logs = activity_response.json()
    approval_log = activity_logs[-1]

    assert approval_log["action"] == (
        "service_request_approved"
    )
    assert approval_log["actor_type"] == "admin"
    assert approval_log["actor_id"] == str(
        admin_auth["admin_id"]
    )
    assert approval_log["details"] == {
        "admin_username": admin_auth["username"],
        "response_edited": False,
    }


def test_approve_service_request_allows_edited_response(
    client: TestClient,
    admin_auth: dict,
) -> None:
    request_id = create_drafted_service_request(client)

    edited_response = (
        "Thank you for your report. "
        "Please stay away from the electrical panel "
        "while the maintenance team reviews the issue."
    )

    response = client.post(
        f"/service-requests/{request_id}/approve",
        headers=admin_auth["headers"],
        json={
            "approved_response": edited_response,
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "approved"
    assert response.json()["approved_response"] == (
        edited_response
    )

    activity_response = client.get(
        f"/service-requests/{request_id}/activity-logs"
    )

    approval_log = activity_response.json()[-1]

    assert approval_log["details"] == {
        "admin_username": admin_auth["username"],
        "response_edited": True,
    }


def test_reject_service_request_saves_reason(
    client: TestClient,
    admin_auth: dict,
) -> None:
    request_id = create_drafted_service_request(client)

    rejection_reason = (
        "The draft promises an action "
        "that has not been confirmed."
    )

    response = client.post(
        f"/service-requests/{request_id}/reject",
        headers=admin_auth["headers"],
        json={
            "reason": rejection_reason,
        },
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["status"] == "rejected"
    assert response_data["approved_response"] is None
    assert response_data["draft_response"] == (
        AI_DRAFT_RESPONSE
    )

    activity_response = client.get(
        f"/service-requests/{request_id}/activity-logs"
    )

    rejection_log = activity_response.json()[-1]

    assert rejection_log["action"] == (
        "service_request_rejected"
    )
    assert rejection_log["actor_type"] == "admin"
    assert rejection_log["actor_id"] == str(
        admin_auth["admin_id"]
    )
    assert rejection_log["details"] == {
        "admin_username": admin_auth["username"],
        "reason": rejection_reason,
    }


def test_approve_rejects_request_that_is_not_drafted(
    client: TestClient,
    admin_auth: dict,
) -> None:
    create_response = client.post(
        "/service-requests",
        json={
            "telegram_chat_id": 111222333,
            "telegram_user_id": 444555666,
            "user_message": (
                "The elevator is not working."
            ),
        },
    )

    assert create_response.status_code == 201

    request_id = create_response.json()["id"]

    response = client.post(
        f"/service-requests/{request_id}/approve",
        headers=admin_auth["headers"],
        json={},
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": (
            "Only drafted service requests "
            "can be reviewed"
        )
    }


def test_approve_returns_404_for_missing_request(
    client: TestClient,
    admin_auth: dict,
) -> None:
    response = client.post(
        "/service-requests/999999999/approve",
        headers=admin_auth["headers"],
        json={},
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Service request not found"
    }


def test_approve_requires_authentication(
    anonymous_client: TestClient,
) -> None:
    response = anonymous_client.post(
        "/service-requests/999999999/approve",
        json={},
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_reject_requires_authentication(
    anonymous_client: TestClient,
) -> None:
    response = anonymous_client.post(
        "/service-requests/999999999/reject",
        json={
            "reason": "The draft must be reviewed again."
        },
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"