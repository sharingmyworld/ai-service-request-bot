import pytest

from app.services.password_service import (
    hash_password,
    verify_password,
)


def test_hash_password_creates_verifiable_hash() -> None:
    plain_password = "StrongPassword123!"

    hashed_password = hash_password(
        plain_password
    )

    assert hashed_password != plain_password
    assert verify_password(
        plain_password,
        hashed_password,
    ) is True


def test_verify_password_rejects_wrong_password() -> None:
    hashed_password = hash_password(
        "CorrectPassword123!"
    )

    assert verify_password(
        "WrongPassword123!",
        hashed_password,
    ) is False


def test_hash_password_rejects_empty_password() -> None:
    with pytest.raises(
        ValueError,
        match="Password cannot be empty",
    ):
        hash_password("")