from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.admin_user import AdminUser
from app.services.password_service import hash_password


class AdminValidationError(ValueError):
    """Raised when administrator data is invalid."""


class AdminUsernameAlreadyExistsError(RuntimeError):
    """Raised when the administrator username is already used."""


def validate_admin_username(username: str) -> str:
    cleaned_username = username.strip()

    if len(cleaned_username) < 3:
        raise AdminValidationError(
            "Username must contain at least 3 characters"
        )

    if len(cleaned_username) > 100:
        raise AdminValidationError(
            "Username cannot exceed 100 characters"
        )

    return cleaned_username


def validate_admin_password(password: str) -> None:
    if len(password) < 12:
        raise AdminValidationError(
            "Password must contain at least 12 characters"
        )

    if len(password) > 128:
        raise AdminValidationError(
            "Password cannot exceed 128 characters"
        )


def create_admin_user(
    database_session: Session,
    username: str,
    password: str,
) -> AdminUser:
    cleaned_username = validate_admin_username(
        username
    )

    validate_admin_password(password)

    existing_admin = database_session.scalar(
        select(AdminUser).where(
            AdminUser.username == cleaned_username
        )
    )

    if existing_admin is not None:
        raise AdminUsernameAlreadyExistsError(
            "Administrator username already exists"
        )

    admin_user = AdminUser(
        username=cleaned_username,
        password_hash=hash_password(password),
        is_active=True,
    )

    try:
        database_session.add(admin_user)
        database_session.commit()
        database_session.refresh(admin_user)

    except IntegrityError as error:
        database_session.rollback()

        raise AdminUsernameAlreadyExistsError(
            "Administrator username already exists"
        ) from error

    except SQLAlchemyError:
        database_session.rollback()
        raise

    return admin_user