from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.activity_log import ActivityLog
from app.models.service_request import (
    ServiceRequest,
    ServiceRequestStatus,
)


def create_service_request(
    database_session: Session,
) -> ServiceRequest:
    marker = uuid4().hex

    service_request = ServiceRequest(
        telegram_chat_id=900001,
        telegram_user_id=900002,
        user_message=(
            f"Administrative details test {marker}"
        ),
        category="plumbing",
        urgency="high",
        location="Kitchen",
        status=ServiceRequestStatus.DRAFTED,
        draft_response=(
            "The maintenance team will review "
            "the reported problem."
        ),
    )

    database_session.add(service_request)
    database_session.commit()
    database_session.refresh(service_request)

    return service_request


def test_admin_service_request_details_require_authentication(
    anonymous_client: TestClient,
) -> None:
    response = anonymous_client.get(
        "/admin/service-requests/1"
    )

    assert response.status_code == 401

    assert response.headers[
        "www-authenticate"
    ] == "Bearer"


def test_admin_can_read_service_request_details(
    client: TestClient,
    database_session: Session,
    admin_auth: dict,
) -> None:
    service_request = create_service_request(
        database_session
    )

    response = client.get(
        (
            "/admin/service-requests/"
            f"{service_request.id}"
        ),
        headers=admin_auth["headers"],
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["id"] == service_request.id
    assert response_data["category"] == "plumbing"
    assert response_data["urgency"] == "high"
    assert response_data["location"] == "Kitchen"
    assert response_data["status"] == "drafted"

    assert response_data["draft_response"] == (
        "The maintenance team will review "
        "the reported problem."
    )


def test_admin_service_request_details_return_404(
    client: TestClient,
    admin_auth: dict,
) -> None:
    response = client.get(
        "/admin/service-requests/999999999",
        headers=admin_auth["headers"],
    )

    assert response.status_code == 404

    assert response.json() == {
        "detail": "Service request not found"
    }


def test_admin_activity_logs_require_authentication(
    anonymous_client: TestClient,
) -> None:
    response = anonymous_client.get(
        "/admin/service-requests/1/activity-logs"
    )

    assert response.status_code == 401

    assert response.headers[
        "www-authenticate"
    ] == "Bearer"


def test_admin_can_read_service_request_activity_logs(
    client: TestClient,
    database_session: Session,
    admin_auth: dict,
) -> None:
    first_request = create_service_request(
        database_session
    )

    second_request = create_service_request(
        database_session
    )

    activity_logs = [
        ActivityLog(
            service_request_id=first_request.id,
            action="service_request_created",
            actor_type="telegram_user",
            actor_id="900002",
            details={
                "source": "test",
            },
        ),
        ActivityLog(
            service_request_id=first_request.id,
            action="ai_analysis_completed",
            actor_type="ai",
            actor_id=None,
            details={
                "category": "plumbing",
                "urgency": "high",
            },
        ),
        ActivityLog(
            service_request_id=second_request.id,
            action="unrelated_request_log",
            actor_type="system",
            actor_id=None,
            details={},
        ),
    ]

    database_session.add_all(
        activity_logs
    )

    database_session.commit()

    response = client.get(
        (
            "/admin/service-requests/"
            f"{first_request.id}/activity-logs"
        ),
        headers=admin_auth["headers"],
    )

    assert response.status_code == 200

    response_data = response.json()

    assert len(response_data) == 2

    actions = [
        activity_log["action"]
        for activity_log in response_data
    ]

    assert actions == [
        "service_request_created",
        "ai_analysis_completed",
    ]

    for activity_log in response_data:
        assert activity_log[
            "service_request_id"
        ] == first_request.id