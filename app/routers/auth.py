from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import CurrentAdmin
from app.models.admin_user import AdminUser
from app.schemas.admin_user import AdminUserRead
from app.schemas.auth import AccessTokenResponse
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