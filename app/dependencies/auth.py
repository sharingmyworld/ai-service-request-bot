from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.admin_user import AdminUser
from app.services.token_service import (
    TokenConfigurationError,
    TokenExpiredError,
    TokenValidationError,
    decode_access_token,
)


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="auth/login",
)


DatabaseSession = Annotated[
    Session,
    Depends(get_db),
]


AccessToken = Annotated[
    str,
    Depends(oauth2_scheme),
]


def create_credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={
            "WWW-Authenticate": "Bearer",
        },
    )


def get_current_admin(
    token: AccessToken,
    database_session: DatabaseSession,
) -> AdminUser:
    try:
        token_subject = decode_access_token(token)

    except TokenConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is not configured",
        ) from error

    except (
        TokenExpiredError,
        TokenValidationError,
    ) as error:
        raise create_credentials_exception() from error

    try:
        admin_id = int(token_subject)

    except ValueError as error:
        raise create_credentials_exception() from error

    admin_user = database_session.get(
        AdminUser,
        admin_id,
    )

    if admin_user is None:
        raise create_credentials_exception()

    if not admin_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator account is inactive",
        )

    return admin_user


CurrentAdmin = Annotated[
    AdminUser,
    Depends(get_current_admin),
]