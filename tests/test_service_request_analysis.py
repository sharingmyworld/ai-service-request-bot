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
from app.services.openai_service import (
    AIAnalysisError,
    OpenAIService,
)


def test_analyze_service_request_saves_ai_result(
    client: TestClient,
) -> None:
    user_message = (
        "Water is leaking under the kitchen sink "
        "in apartment 12."
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
            category=ProblemCategory.PLUMBING,
            urgency=UrgencyLevel.HIGH,
            location="Kitchen, apartment 12",
            summary=(
                "Water is leaking from the pipe "
                "under the kitchen sink."
            ),
            draft_response=(
                "Thank you for reporting the leak. "
                "The maintenance team will review "
                "your request."
            ),
        )
    )

    app.dependency_overrides[
        provide_openai_service
    ] = lambda: mock_ai_service

    response = client.post(
        f"/service-requests/{request_id}/analyze"
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["id"] == request_id
    assert response_data["category"] == "plumbing"
    assert response_data["urgency"] == "high"
    assert response_data["location"] == (
        "Kitchen, apartment 12"
    )
    assert response_data["status"] == "drafted"
    assert response_data["draft_response"] == (
        "Thank you for reporting the leak. "
        "The maintenance team will review "
        "your request."
    )
    assert response_data["approved_response"] is None

    mock_ai_service.analyze_service_request.assert_called_once_with(
        user_message
    )

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
    assert activity_logs[1]["actor_type"] == "ai"
    assert activity_logs[1]["actor_id"] is None
    assert activity_logs[1]["details"] == {
        "category": "plumbing",
        "urgency": "high",
        "location": "Kitchen, apartment 12",
        "summary": (
            "Water is leaking from the pipe "
            "under the kitchen sink."
        ),
    }


def test_analyze_service_request_returns_404_when_missing(
    client: TestClient,
) -> None:
    mock_ai_service = Mock(
        spec=OpenAIService
    )

    app.dependency_overrides[
        provide_openai_service
    ] = lambda: mock_ai_service

    response = client.post(
        "/service-requests/999999999/analyze"
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Service request not found"
    }

    mock_ai_service.analyze_service_request.assert_not_called()


def test_analyze_service_request_returns_503_when_ai_fails(
    client: TestClient,
) -> None:
    create_response = client.post(
        "/service-requests",
        json={
            "telegram_chat_id": 111222333,
            "telegram_user_id": 444555666,
            "user_message": (
                "The heating is not working "
                "in apartment 8."
            ),
        },
    )

    assert create_response.status_code == 201

    request_id = create_response.json()["id"]

    mock_ai_service = Mock(
        spec=OpenAIService
    )

    mock_ai_service.analyze_service_request.side_effect = (
        AIAnalysisError(
            "OpenAI did not return a valid analysis"
        )
    )

    app.dependency_overrides[
        provide_openai_service
    ] = lambda: mock_ai_service

    response = client.post(
        f"/service-requests/{request_id}/analyze"
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "AI analysis failed"
    }

    request_response = client.get(
        f"/service-requests/{request_id}"
    )

    assert request_response.status_code == 200
    assert request_response.json()["status"] == "new"
    assert request_response.json()["category"] is None
    assert request_response.json()["draft_response"] is None