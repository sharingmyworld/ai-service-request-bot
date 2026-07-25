import pytest
from sqlalchemy.orm import Session

from app.services.admin_service import (
    AdminUsernameAlreadyExistsError,
    AdminValidationError,
    create_admin_user,
)
from app.services.password_service import verify_password


def test_create_admin_user_saves_active_account(
    database_session: Session,
) -> None:
    admin_user = create_admin_user(
        database_session=database_session,
        username="  command-admin  ",
        password="StrongCommandPassword123!",
    )

    assert admin_user.id > 0
    assert admin_user.username == "command-admin"
    assert admin_user.is_active is True
    assert admin_user.created_at is not None

    assert verify_password(
        plain_password="StrongCommandPassword123!",
        hashed_password=admin_user.password_hash,
    ) is True


def test_create_admin_user_rejects_duplicate_username(
    database_session: Session,
) -> None:
    create_admin_user(
        database_session=database_session,
        username="duplicate-admin",
        password="StrongCommandPassword123!",
    )

    with pytest.raises(
        AdminUsernameAlreadyExistsError,
        match="Administrator username already exists",
    ):
        create_admin_user(
            database_session=database_session,
            username="duplicate-admin",
            password="AnotherStrongPassword123!",
        )


def test_create_admin_user_rejects_short_username(
    database_session: Session,
) -> None:
    with pytest.raises(
        AdminValidationError,
        match="Username must contain at least 3 characters",
    ):
        create_admin_user(
            database_session=database_session,
            username="ab",
            password="StrongCommandPassword123!",
        )


def test_create_admin_user_rejects_short_password(
    database_session: Session,
) -> None:
    with pytest.raises(
        AdminValidationError,
        match="Password must contain at least 12 characters",
    ):
        create_admin_user(
            database_session=database_session,
            username="short-password-admin",
            password="short",
        )