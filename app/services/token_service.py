from datetime import datetime, timedelta, timezone

import jwt
from jwt import (
    ExpiredSignatureError,
    InvalidTokenError as PyJWTInvalidTokenError,
)

from app.config import settings


class TokenConfigurationError(RuntimeError):
    """Raised when JWT configuration is missing."""


class TokenValidationError(RuntimeError):
    """Raised when a JWT token is invalid."""


class TokenExpiredError(TokenValidationError):
    """Raised when a JWT token has expired."""


def get_jwt_secret_key(
    secret_key: str | None = None,
) -> str:
    resolved_secret = (
        secret_key
        if secret_key is not None
        else settings.jwt_secret_key
    )

    if (
        resolved_secret is None
        or not resolved_secret.strip()
    ):
        raise TokenConfigurationError(
            "JWT_SECRET_KEY is not configured"
        )

    return resolved_secret.strip()


def get_jwt_algorithm(
    algorithm: str | None = None,
) -> str:
    resolved_algorithm = (
        algorithm
        if algorithm is not None
        else settings.jwt_algorithm
    )

    if not resolved_algorithm.strip():
        raise TokenConfigurationError(
            "JWT_ALGORITHM is not configured"
        )

    return resolved_algorithm.strip()


def create_access_token(
    subject: str,
    secret_key: str | None = None,
    algorithm: str | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    cleaned_subject = subject.strip()

    if not cleaned_subject:
        raise ValueError(
            "Token subject cannot be empty"
        )

    resolved_secret = get_jwt_secret_key(
        secret_key
    )

    resolved_algorithm = get_jwt_algorithm(
        algorithm
    )

    current_time = datetime.now(timezone.utc)

    expiration_time = current_time + (
        expires_delta
        if expires_delta is not None
        else timedelta(
            minutes=(
                settings.jwt_access_token_expire_minutes
            )
        )
    )

    payload = {
        "sub": cleaned_subject,
        "type": "access",
        "iat": current_time,
        "exp": expiration_time,
    }

    return jwt.encode(
        payload,
        resolved_secret,
        algorithm=resolved_algorithm,
    )


def decode_access_token(
    token: str,
    secret_key: str | None = None,
    algorithm: str | None = None,
) -> str:
    cleaned_token = token.strip()

    if not cleaned_token:
        raise TokenValidationError(
            "Access token cannot be empty"
        )

    resolved_secret = get_jwt_secret_key(
        secret_key
    )

    resolved_algorithm = get_jwt_algorithm(
        algorithm
    )

    try:
        payload = jwt.decode(
            cleaned_token,
            resolved_secret,
            algorithms=[
                resolved_algorithm
            ],
            options={
                "require": [
                    "sub",
                    "type",
                    "iat",
                    "exp",
                ],
            },
        )

    except ExpiredSignatureError as error:
        raise TokenExpiredError(
            "Access token has expired"
        ) from error

    except PyJWTInvalidTokenError as error:
        raise TokenValidationError(
            "Access token is invalid"
        ) from error

    if payload.get("type") != "access":
        raise TokenValidationError(
            "Token is not an access token"
        )

    subject = payload.get("sub")

    if (
        not isinstance(subject, str)
        or not subject.strip()
    ):
        raise TokenValidationError(
            "Access token subject is invalid"
        )

    return subject.strip()