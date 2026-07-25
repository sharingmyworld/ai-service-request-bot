from datetime import timedelta

import pytest

from app.services.token_service import (
    TokenExpiredError,
    TokenValidationError,
    create_access_token,
    decode_access_token,
)


TEST_SECRET_KEY = (
    "test-secret-key-that-is-long-enough-"
    "for-jwt-token-tests-123456789"
)

TEST_ALGORITHM = "HS256"


def test_access_token_contains_subject() -> None:
    token = create_access_token(
        subject="123",
        secret_key=TEST_SECRET_KEY,
        algorithm=TEST_ALGORITHM,
    )

    decoded_subject = decode_access_token(
        token=token,
        secret_key=TEST_SECRET_KEY,
        algorithm=TEST_ALGORITHM,
    )

    assert decoded_subject == "123"


def test_access_token_rejects_wrong_secret() -> None:
    token = create_access_token(
        subject="123",
        secret_key=TEST_SECRET_KEY,
        algorithm=TEST_ALGORITHM,
    )

    with pytest.raises(
        TokenValidationError,
        match="Access token is invalid",
    ):
        decode_access_token(
            token=token,
            secret_key=(
                "different-test-secret-key-"
                "that-cannot-verify-the-token"
            ),
            algorithm=TEST_ALGORITHM,
        )


def test_access_token_rejects_expired_token() -> None:
    token = create_access_token(
        subject="123",
        secret_key=TEST_SECRET_KEY,
        algorithm=TEST_ALGORITHM,
        expires_delta=timedelta(
            seconds=-1
        ),
    )

    with pytest.raises(
        TokenExpiredError,
        match="Access token has expired",
    ):
        decode_access_token(
            token=token,
            secret_key=TEST_SECRET_KEY,
            algorithm=TEST_ALGORITHM,
        )


def test_access_token_rejects_empty_subject() -> None:
    with pytest.raises(
        ValueError,
        match="Token subject cannot be empty",
    ):
        create_access_token(
            subject="   ",
            secret_key=TEST_SECRET_KEY,
            algorithm=TEST_ALGORITHM,
        )