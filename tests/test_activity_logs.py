from fastapi.testclient import TestClient


def test_create_service_request_creates_activity_log(
    client: TestClient,
) -> None:
    user_message = (
        "There is no electricity in the apartment."
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

    created_request = create_response.json()
    request_id = created_request["id"]

    response = client.get(
        f"/service-requests/{request_id}/activity-logs"
    )

    assert response.status_code == 200

    activity_logs = response.json()

    assert len(activity_logs) == 1

    activity_log = activity_logs[0]

    assert activity_log["service_request_id"] == request_id
    assert activity_log["action"] == (
        "service_request_created"
    )
    assert activity_log["actor_type"] == "telegram_user"
    assert activity_log["actor_id"] == "987654321"
    assert activity_log["details"] == {
        "telegram_chat_id": 123456789,
        "message_length": len(user_message),
    }
    assert activity_log["created_at"] is not None


def test_get_activity_logs_returns_404_for_missing_request(
    client: TestClient,
) -> None:
    response = client.get(
        "/service-requests/999999999/activity-logs"
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Service request not found"
    }