import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import settings
from app.models.admin_user import AdminUser
from app.services.password_service import hash_password
from app.services.token_service import create_access_token


TEST_JWT_SECRET = (
    "test-jwt-secret-key-that-is-long-enough-"
    "for-current-admin-tests-123456789"
)


@pytest.fixture
def configured_jwt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        settings,
        "jwt_secret_key",
        TEST_JWT_SECRET,
    )

    monkeypatch.setattr(
        settings,
        "jwt_algorithm",
        "HS256",
    )

    monkeypatch.setattr(
        settings,
        "jwt_access_token_expire_minutes",
        30,
    )


def create_admin_user(
    database_session: Session,
    username: str,
    is_active: bool = True,
) -> AdminUser:
    admin_user = AdminUser(
        username=username,
        password_hash=hash_password(
            "StrongAdminPassword123!"
        ),
        is_active=is_active,
    )

    database_session.add(admin_user)
    database_session.commit()
    database_session.refresh(admin_user)

    return admin_user


def create_authorization_headers(
    admin_id: int,
) -> dict[str, str]:
    access_token = create_access_token(
        subject=str(admin_id)
    )

    return {
        "Authorization": f"Bearer {access_token}"
    }


def test_authenticated_admin_can_read_own_profile(
    client: TestClient,
    database_session: Session,
    configured_jwt: None,
) -> None:
    admin_user = create_admin_user(
        database_session=database_session,
        username="current-admin",
    )

    response = client.get(
        "/auth/me",
        headers=create_authorization_headers(
            admin_user.id
        ),
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["id"] == admin_user.id
    assert response_data["username"] == "current-admin"
    assert response_data["is_active"] is True
    assert response_data["created_at"] is not None
    assert "password_hash" not in response_data


def test_current_admin_requires_access_token(
    client: TestClient,
    configured_jwt: None,
) -> None:
    response = client.get(
        "/auth/me"
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_current_admin_rejects_invalid_token(
    client: TestClient,
    configured_jwt: None,
) -> None:
    response = client.get(
        "/auth/me",
        headers={
            "Authorization": "Bearer invalid-token"
        },
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Could not validate credentials"
    }
    assert response.headers["www-authenticate"] == "Bearer"


def test_inactive_admin_cannot_read_profile(
    client: TestClient,
    database_session: Session,
    configured_jwt: None,
) -> None:
    admin_user = create_admin_user(
        database_session=database_session,
        username="inactive-current-admin",
        is_active=False,
    )

    response = client.get(
        "/auth/me",
        headers=create_authorization_headers(
            admin_user.id
        ),
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Administrator account is inactive"
    }