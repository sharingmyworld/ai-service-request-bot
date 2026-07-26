from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.service_request import (
    ServiceRequest,
    ServiceRequestStatus,
)


def create_request(
    database_session: Session,
    marker: str,
    number: int,
    request_status: ServiceRequestStatus,
    category: str | None = None,
    urgency: str | None = None,
    location: str | None = None,
) -> ServiceRequest:
    draft_response = None
    approved_response = None

    if request_status in {
        ServiceRequestStatus.DRAFTED,
        ServiceRequestStatus.APPROVED,
        ServiceRequestStatus.SENT,
    }:
        draft_response = (
            "The service request has been reviewed."
        )

    if request_status in {
        ServiceRequestStatus.APPROVED,
        ServiceRequestStatus.SENT,
    }:
        approved_response = (
            "The maintenance team will review "
            "the reported issue."
        )

    service_request = ServiceRequest(
        telegram_chat_id=700000 + number,
        telegram_user_id=800000 + number,
        user_message=(
            f"{marker} service request number {number}"
        ),
        category=category,
        urgency=urgency,
        location=location,
        status=request_status,
        draft_response=draft_response,
        approved_response=approved_response,
    )

    database_session.add(service_request)
    database_session.commit()
    database_session.refresh(service_request)

    return service_request


def test_admin_service_requests_requires_authentication(
    client: TestClient,
) -> None:
    response = client.get(
        "/admin/service-requests"
    )

    assert response.status_code == 401

    assert response.headers[
        "www-authenticate"
    ] == "Bearer"


def test_admin_service_requests_supports_pagination(
    client: TestClient,
    database_session: Session,
    admin_auth: dict,
) -> None:
    marker = (
        f"pagination-{uuid4().hex}"
    )

    created_requests = [
        create_request(
            database_session=database_session,
            marker=marker,
            number=number,
            request_status=ServiceRequestStatus.NEW,
        )
        for number in range(1, 4)
    ]

    first_response = client.get(
        "/admin/service-requests",
        headers=admin_auth["headers"],
        params={
            "search": marker,
            "offset": 0,
            "limit": 2,
        },
    )

    assert first_response.status_code == 200

    first_page = first_response.json()

    assert first_page["total"] == 3
    assert first_page["offset"] == 0
    assert first_page["limit"] == 2
    assert len(first_page["items"]) == 2

    second_response = client.get(
        "/admin/service-requests",
        headers=admin_auth["headers"],
        params={
            "search": marker,
            "offset": 2,
            "limit": 2,
        },
    )

    assert second_response.status_code == 200

    second_page = second_response.json()

    assert second_page["total"] == 3
    assert second_page["offset"] == 2
    assert second_page["limit"] == 2
    assert len(second_page["items"]) == 1

    returned_ids = {
        request_data["id"]
        for request_data in (
            first_page["items"]
            + second_page["items"]
        )
    }

    expected_ids = {
        service_request.id
        for service_request in created_requests
    }

    assert returned_ids == expected_ids


def test_admin_service_requests_filters_by_status(
    client: TestClient,
    database_session: Session,
    admin_auth: dict,
) -> None:
    marker = (
        f"status-filter-{uuid4().hex}"
    )

    drafted_request = create_request(
        database_session=database_session,
        marker=marker,
        number=10,
        request_status=ServiceRequestStatus.DRAFTED,
    )

    create_request(
        database_session=database_session,
        marker=marker,
        number=11,
        request_status=ServiceRequestStatus.SENT,
    )

    response = client.get(
        "/admin/service-requests",
        headers=admin_auth["headers"],
        params={
            "search": marker,
            "status": "drafted",
        },
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["total"] == 1
    assert len(response_data["items"]) == 1

    returned_request = response_data["items"][0]

    assert returned_request["id"] == (
        drafted_request.id
    )

    assert returned_request["status"] == "drafted"


def test_admin_service_requests_filters_category_and_urgency(
    client: TestClient,
    database_session: Session,
    admin_auth: dict,
) -> None:
    marker = (
        f"category-filter-{uuid4().hex}"
    )

    matching_request = create_request(
        database_session=database_session,
        marker=marker,
        number=20,
        request_status=ServiceRequestStatus.DRAFTED,
        category="electrical",
        urgency="critical",
        location="Basement",
    )

    create_request(
        database_session=database_session,
        marker=marker,
        number=21,
        request_status=ServiceRequestStatus.DRAFTED,
        category="plumbing",
        urgency="high",
        location="Kitchen",
    )

    response = client.get(
        "/admin/service-requests",
        headers=admin_auth["headers"],
        params={
            "search": marker,
            "category": "electrical",
            "urgency": "critical",
        },
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["total"] == 1

    returned_request = response_data["items"][0]

    assert returned_request["id"] == (
        matching_request.id
    )

    assert returned_request["category"] == (
        "electrical"
    )

    assert returned_request["urgency"] == (
        "critical"
    )


def test_admin_service_requests_search_is_case_insensitive(
    client: TestClient,
    database_session: Session,
    admin_auth: dict,
) -> None:
    marker = (
        f"UniqueBoilerRoom{uuid4().hex}"
    )

    matching_request = create_request(
        database_session=database_session,
        marker="unrelated-message",
        number=30,
        request_status=ServiceRequestStatus.NEW,
        location=marker,
    )

    response = client.get(
        "/admin/service-requests",
        headers=admin_auth["headers"],
        params={
            "search": marker.lower(),
        },
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["total"] == 1

    assert response_data["items"][0]["id"] == (
        matching_request.id
    )


def test_admin_service_requests_rejects_invalid_parameters(
    client: TestClient,
    admin_auth: dict,
) -> None:
    invalid_limit_response = client.get(
        "/admin/service-requests",
        headers=admin_auth["headers"],
        params={
            "limit": 101,
        },
    )

    assert invalid_limit_response.status_code == 422

    invalid_status_response = client.get(
        "/admin/service-requests",
        headers=admin_auth["headers"],
        params={
            "status": "unknown-status",
        },
    )

    assert invalid_status_response.status_code == 422