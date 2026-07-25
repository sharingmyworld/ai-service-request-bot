from sqlalchemy.orm import Session

from app.models.admin_user import AdminUser
from app.services.password_service import (
    hash_password,
    verify_password,
)


def test_admin_user_can_be_saved(
    database_session: Session,
) -> None:
    plain_password = "StrongAdminPassword123!"

    admin_user = AdminUser(
        username="portfolio-admin",
        password_hash=hash_password(
            plain_password
        ),
    )

    database_session.add(admin_user)
    database_session.commit()
    database_session.refresh(admin_user)

    assert admin_user.id > 0
    assert admin_user.username == "portfolio-admin"
    assert admin_user.is_active is True
    assert admin_user.created_at is not None
    assert admin_user.password_hash != plain_password

    assert verify_password(
        plain_password,
        admin_user.password_hash,
    ) is True