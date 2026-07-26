from fastapi.testclient import TestClient


def assert_bearer_authentication_required(
    response,
) -> None:
    assert response.status_code == 401

    assert response.headers[
        "www-authenticate"
    ] == "Bearer"


def test_service_request_list_requires_authentication(
    anonymous_client: TestClient,
) -> None:
    response = anonymous_client.get(
        "/service-requests"
    )

    assert_bearer_authentication_required(
        response
    )


def test_service_request_details_require_authentication(
    anonymous_client: TestClient,
) -> None:
    response = anonymous_client.get(
        "/service-requests/1"
    )

    assert_bearer_authentication_required(
        response
    )


def test_manual_ai_analysis_requires_authentication(
    anonymous_client: TestClient,
) -> None:
    response = anonymous_client.post(
        "/service-requests/1/analyze"
    )

    assert_bearer_authentication_required(
        response
    )


def test_activity_logs_require_authentication(
    anonymous_client: TestClient,
) -> None:
    response = anonymous_client.get(
        "/service-requests/1/activity-logs"
    )

    assert_bearer_authentication_required(
        response
    )