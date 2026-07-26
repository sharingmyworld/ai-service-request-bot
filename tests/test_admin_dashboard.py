from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.service_request import (
    ServiceRequest,
    ServiceRequestStatus,
)


def get_count(
    counts: dict[str, int],
    key: str,
) -> int:
    return counts.get(
        key,
        0,
    )


def test_admin_dashboard_requires_authentication(
    anonymous_client: TestClient,
) -> None:
    response = anonymous_client.get(
        "/admin/dashboard"
    )

    assert response.status_code == 401

    assert response.headers[
        "www-authenticate"
    ] == "Bearer"


def test_admin_dashboard_returns_request_statistics(
    client: TestClient,
    database_session: Session,
    admin_auth: dict,
) -> None:
    baseline_response = client.get(
        "/admin/dashboard",
        headers=admin_auth["headers"],
    )

    assert baseline_response.status_code == 200

    baseline = baseline_response.json()

    service_requests = [
        ServiceRequest(
            telegram_chat_id=100001,
            telegram_user_id=200001,
            user_message=(
                "Water is leaking in the kitchen."
            ),
            category="plumbing",
            urgency="high",
            location="Kitchen",
            status=ServiceRequestStatus.DRAFTED,
            draft_response=(
                "The request has been received."
            ),
        ),
        ServiceRequest(
            telegram_chat_id=100002,
            telegram_user_id=200002,
            user_message=(
                "There are sparks near the panel."
            ),
            category="electrical",
            urgency="critical",
            location="Basement",
            status=ServiceRequestStatus.APPROVED,
            draft_response=(
                "Please stay away from the panel."
            ),
            approved_response=(
                "Please stay away from the panel."
            ),
        ),
        ServiceRequest(
            telegram_chat_id=100003,
            telegram_user_id=200003,
            user_message=(
                "The electrical issue was repaired."
            ),
            category="electrical",
            urgency="critical",
            location="Hallway",
            status=ServiceRequestStatus.SENT,
            draft_response=(
                "The issue will be reviewed."
            ),
            approved_response=(
                "The issue has been resolved."
            ),
        ),
        ServiceRequest(
            telegram_chat_id=100004,
            telegram_user_id=200004,
            user_message=(
                "A new request without AI analysis."
            ),
            status=ServiceRequestStatus.NEW,
        ),
    ]

    database_session.add_all(
        service_requests
    )

    database_session.commit()

    response = client.get(
        "/admin/dashboard",
        headers=admin_auth["headers"],
    )

    assert response.status_code == 200

    dashboard = response.json()

    assert dashboard["total_requests"] == (
        baseline["total_requests"] + 4
    )

    assert dashboard["status_counts"]["new"] == (
        baseline["status_counts"]["new"] + 1
    )

    assert dashboard["status_counts"]["drafted"] == (
        baseline["status_counts"]["drafted"] + 1
    )

    assert dashboard["status_counts"]["approved"] == (
        baseline["status_counts"]["approved"] + 1
    )

    assert dashboard["status_counts"]["sent"] == (
        baseline["status_counts"]["sent"] + 1
    )

    assert get_count(
        dashboard["category_counts"],
        "plumbing",
    ) == (
        get_count(
            baseline["category_counts"],
            "plumbing",
        )
        + 1
    )

    assert get_count(
        dashboard["category_counts"],
        "electrical",
    ) == (
        get_count(
            baseline["category_counts"],
            "electrical",
        )
        + 2
    )

    assert get_count(
        dashboard["urgency_counts"],
        "high",
    ) == (
        get_count(
            baseline["urgency_counts"],
            "high",
        )
        + 1
    )

    assert get_count(
        dashboard["urgency_counts"],
        "critical",
    ) == (
        get_count(
            baseline["urgency_counts"],
            "critical",
        )
        + 2
    )

    assert dashboard["pending_review"] == (
        dashboard["status_counts"]["drafted"]
    )

    assert dashboard["approved_not_sent"] == (
        dashboard["status_counts"]["approved"]
    )

    assert dashboard["critical_requests"] == (
        dashboard["urgency_counts"]["critical"]
    )