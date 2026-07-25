from fastapi.testclient import TestClient


def test_create_service_request(
    client: TestClient,
) -> None:
    response = client.post(
        "/service-requests",
        json={
            "telegram_chat_id": 123456789,
            "telegram_user_id": 987654321,
            "user_message": (
                "Water is leaking under the kitchen sink."
            ),
        },
    )

    assert response.status_code == 201

    response_data = response.json()

    assert response_data["id"] > 0
    assert response_data["telegram_chat_id"] == 123456789
    assert response_data["telegram_user_id"] == 987654321
    assert response_data["user_message"] == (
        "Water is leaking under the kitchen sink."
    )
    assert response_data["status"] == "new"
    assert response_data["category"] is None
    assert response_data["urgency"] is None
    assert response_data["location"] is None
    assert response_data["draft_response"] is None
    assert response_data["approved_response"] is None
    assert response_data["created_at"] is not None
    assert response_data["updated_at"] is not None


def test_create_service_request_rejects_short_message(
    client: TestClient,
) -> None:
    response = client.post(
        "/service-requests",
        json={
            "telegram_chat_id": 123456789,
            "telegram_user_id": 987654321,
            "user_message": "Hi",
        },
    )

    assert response.status_code == 422


def test_get_service_requests_returns_created_request(
    client: TestClient,
) -> None:
    create_response = client.post(
        "/service-requests",
        json={
            "telegram_chat_id": 111222333,
            "telegram_user_id": 444555666,
            "user_message": (
                "The heating is not working in apartment 12."
            ),
        },
    )

    assert create_response.status_code == 201

    created_request = create_response.json()

    response = client.get(
        "/service-requests"
    )

    assert response.status_code == 200

    response_data = response.json()

    created_request_ids = [
        service_request["id"]
        for service_request in response_data
    ]

    assert created_request["id"] in created_request_ids


def test_get_service_request_returns_request_by_id(
    client: TestClient,
) -> None:
    create_response = client.post(
        "/service-requests",
        json={
            "telegram_chat_id": 999888777,
            "telegram_user_id": 666555444,
            "user_message": (
                "The elevator is stuck on the third floor."
            ),
        },
    )

    assert create_response.status_code == 201

    created_request = create_response.json()
    request_id = created_request["id"]

    response = client.get(
        f"/service-requests/{request_id}"
    )

    assert response.status_code == 200
    assert response.json()["id"] == request_id
    assert response.json()["user_message"] == (
        "The elevator is stuck on the third floor."
    )


def test_get_service_request_returns_404_when_not_found(
    client: TestClient,
) -> None:
    response = client.get(
        "/service-requests/999999999"
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Service request not found"
    }