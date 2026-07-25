from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import settings
from app.models.admin_user import AdminUser
from app.services.password_service import hash_password
from app.services.token_service import decode_access_token


TEST_JWT_SECRET = (
    "test-jwt-secret-key-that-is-long-enough-"
    "for-admin-login-tests-123456789"
)

TEST_ADMIN_PASSWORD = "StrongAdminPassword123!"


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
    username: str | None = None,
    password: str = TEST_ADMIN_PASSWORD,
    is_active: bool = True,
) -> AdminUser:
    resolved_username = (
        username
        if username is not None
        else f"login-admin-{uuid4().hex}"
    )

    admin_user = AdminUser(
        username=resolved_username,
        password_hash=hash_password(password),
        is_active=is_active,
    )

    database_session.add(admin_user)
    database_session.commit()
    database_session.refresh(admin_user)

    return admin_user


def test_admin_can_log_in(
    client: TestClient,
    database_session: Session,
    configured_jwt: None,
) -> None:
    admin_user = create_admin_user(
        database_session
    )

    response = client.post(
        "/auth/login",
        data={
            "username": admin_user.username,
            "password": TEST_ADMIN_PASSWORD,
        },
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["token_type"] == "bearer"

    assert isinstance(
        response_data["access_token"],
        str,
    )

    assert response_data["access_token"]

    token_subject = decode_access_token(
        token=response_data["access_token"],
        secret_key=TEST_JWT_SECRET,
        algorithm="HS256",
    )

    assert token_subject == str(admin_user.id)


def test_admin_login_rejects_wrong_password(
    client: TestClient,
    database_session: Session,
    configured_jwt: None,
) -> None:
    admin_user = create_admin_user(
        database_session
    )

    response = client.post(
        "/auth/login",
        data={
            "username": admin_user.username,
            "password": "WrongPassword123!",
        },
    )

    assert response.status_code == 401

    assert response.json() == {
        "detail": "Incorrect username or password"
    }

    assert response.headers["www-authenticate"] == (
        "Bearer"
    )


def test_admin_login_rejects_unknown_username(
    client: TestClient,
    configured_jwt: None,
) -> None:
    unknown_username = (
        f"unknown-admin-{uuid4().hex}"
    )

    response = client.post(
        "/auth/login",
        data={
            "username": unknown_username,
            "password": TEST_ADMIN_PASSWORD,
        },
    )

    assert response.status_code == 401

    assert response.json() == {
        "detail": "Incorrect username or password"
    }

    assert response.headers["www-authenticate"] == (
        "Bearer"
    )


def test_inactive_admin_cannot_log_in(
    client: TestClient,
    database_session: Session,
    configured_jwt: None,
) -> None:
    admin_user = create_admin_user(
        database_session,
        username=(
            f"inactive-admin-{uuid4().hex}"
        ),
        is_active=False,
    )

    response = client.post(
        "/auth/login",
        data={
            "username": admin_user.username,
            "password": TEST_ADMIN_PASSWORD,
        },
    )

    assert response.status_code == 403

    assert response.json() == {
        "detail": (
            "Administrator account is inactive"
        )
    }