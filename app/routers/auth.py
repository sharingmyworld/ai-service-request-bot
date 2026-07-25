from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import CurrentAdmin
from app.models.admin_user import AdminUser
from app.schemas.admin_user import AdminUserRead
from app.schemas.auth import (
    AccessTokenResponse,
    PasswordChangeRequest,
    PasswordChangeResponse,
)
from app.services.admin_service import (
    AdminCurrentPasswordInvalidError,
    AdminPasswordReuseError,
    AdminValidationError,
    change_admin_password,
)
from app.services.password_service import verify_password
from app.services.token_service import (
    TokenConfigurationError,
    create_access_token,
)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


DatabaseSession = Annotated[
    Session,
    Depends(get_db),
]


LoginForm = Annotated[
    OAuth2PasswordRequestForm,
    Depends(),
]


def authenticate_admin(
    username: str,
    password: str,
    database_session: Session,
) -> AdminUser | None:
    statement = select(AdminUser).where(
        AdminUser.username == username
    )

    admin_user = database_session.scalar(
        statement
    )

    if admin_user is None:
        return None

    password_is_valid = verify_password(
        plain_password=password,
        hashed_password=admin_user.password_hash,
    )

    if not password_is_valid:
        return None

    return admin_user


@router.post(
    "/login",
    response_model=AccessTokenResponse,
)
def login_admin(
    form_data: LoginForm,
    database_session: DatabaseSession,
) -> AccessTokenResponse:
    admin_user = authenticate_admin(
        username=form_data.username,
        password=form_data.password,
        database_session=database_session,
    )

    if admin_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    if not admin_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator account is inactive",
        )

    try:
        access_token = create_access_token(
            subject=str(admin_user.id)
        )

    except TokenConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is not configured",
        ) from error

    return AccessTokenResponse(
        access_token=access_token,
        token_type="bearer",
    )


@router.get(
    "/me",
    response_model=AdminUserRead,
)
def read_current_admin(
    current_admin: CurrentAdmin,
) -> AdminUser:
    return current_admin


@router.post(
    "/change-password",
    response_model=PasswordChangeResponse,
)
def change_current_admin_password(
    password_data: PasswordChangeRequest,
    current_admin: CurrentAdmin,
    database_session: DatabaseSession,
) -> PasswordChangeResponse:
    try:
        change_admin_password(
            database_session=database_session,
            admin_user=current_admin,
            current_password=(
                password_data.current_password
            ),
            new_password=password_data.new_password,
        )

    except AdminCurrentPasswordInvalidError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        ) from error

    except AdminPasswordReuseError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "New password must be different "
                "from the current password"
            ),
        ) from error

    except AdminValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error

    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password could not be changed",
        ) from error

    return PasswordChangeResponse(
        message="Password changed successfully"
    )