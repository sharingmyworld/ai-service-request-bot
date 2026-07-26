import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import settings
from app.models.admin_user import AdminUser
from app.services.password_service import (
    hash_password,
    verify_password,
)
from app.services.token_service import create_access_token


TEST_JWT_SECRET = (
    "test-jwt-secret-key-that-is-long-enough-"
    "for-password-change-tests-123456789"
)

CURRENT_PASSWORD = "CurrentStrongPassword123!"
NEW_PASSWORD = "NewStrongPassword456!"


@pytest.fixture
def password_change_admin(
    database_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> dict:
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

    admin_user = AdminUser(
        username="password-change-admin",
        password_hash=hash_password(
            CURRENT_PASSWORD
        ),
        is_active=True,
    )

    database_session.add(admin_user)
    database_session.commit()
    database_session.refresh(admin_user)

    access_token = create_access_token(
        subject=str(admin_user.id)
    )

    return {
        "admin_user": admin_user,
        "headers": {
            "Authorization": (
                f"Bearer {access_token}"
            )
        },
    }


def test_admin_can_change_password(
    client: TestClient,
    database_session: Session,
    password_change_admin: dict,
) -> None:
    admin_user = password_change_admin[
        "admin_user"
    ]

    response = client.post(
        "/auth/change-password",
        headers=password_change_admin["headers"],
        json={
            "current_password": CURRENT_PASSWORD,
            "new_password": NEW_PASSWORD,
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": "Password changed successfully"
    }

    database_session.refresh(admin_user)

    assert verify_password(
        CURRENT_PASSWORD,
        admin_user.password_hash,
    ) is False

    assert verify_password(
        NEW_PASSWORD,
        admin_user.password_hash,
    ) is True


def test_password_change_rejects_wrong_current_password(
    client: TestClient,
    database_session: Session,
    password_change_admin: dict,
) -> None:
    admin_user = password_change_admin[
        "admin_user"
    ]

    response = client.post(
        "/auth/change-password",
        headers=password_change_admin["headers"],
        json={
            "current_password": "WrongPassword123!",
            "new_password": NEW_PASSWORD,
        },
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Current password is incorrect"
    }

    database_session.refresh(admin_user)

    assert verify_password(
        CURRENT_PASSWORD,
        admin_user.password_hash,
    ) is True


def test_password_change_rejects_reused_password(
    client: TestClient,
    password_change_admin: dict,
) -> None:
    response = client.post(
        "/auth/change-password",
        headers=password_change_admin["headers"],
        json={
            "current_password": CURRENT_PASSWORD,
            "new_password": CURRENT_PASSWORD,
        },
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": (
            "New password must be different "
            "from the current password"
        )
    }


def test_password_change_requires_authentication(
    anonymous_client: TestClient,
) -> None:
    response = anonymous_client.post(
        "/auth/change-password",
        json={
            "current_password": CURRENT_PASSWORD,
            "new_password": NEW_PASSWORD,
        },
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"