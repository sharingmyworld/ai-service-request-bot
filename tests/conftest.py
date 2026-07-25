from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import settings
from app.database import engine, get_db
from app.main import app
from app.models.admin_user import AdminUser
from app.services.token_service import create_access_token


TEST_JWT_SECRET = (
    "test-jwt-secret-key-that-is-long-enough-"
    "for-protected-endpoint-tests-123456789"
)


@pytest.fixture
def database_session() -> Generator[Session, None, None]:
    connection = engine.connect()
    transaction = connection.begin()

    session = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
    )

    try:
        yield session

    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(
    database_session: Session,
) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield database_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def admin_auth(
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
        username="protected-endpoint-admin",
        password_hash=(
            "not-used-in-protected-endpoint-tests"
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
        "admin_id": admin_user.id,
        "username": admin_user.username,
        "headers": {
            "Authorization": (
                f"Bearer {access_token}"
            )
        },
    }