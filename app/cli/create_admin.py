import argparse
import getpass

from sqlalchemy.exc import SQLAlchemyError

from app.database import SessionLocal
from app.services.admin_service import (
    AdminUsernameAlreadyExistsError,
    AdminValidationError,
    create_admin_user,
)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Create an administrator account "
            "for AI Service Request Bot."
        )
    )

    parser.add_argument(
        "--username",
        required=True,
        help="Username of the new administrator.",
    )

    return parser


def main() -> int:
    parser = build_argument_parser()
    arguments = parser.parse_args()

    password = getpass.getpass(
        "Administrator password: "
    )

    password_confirmation = getpass.getpass(
        "Confirm administrator password: "
    )

    if password != password_confirmation:
        print(
            "Error: Passwords do not match."
        )
        return 1

    with SessionLocal() as database_session:
        try:
            admin_user = create_admin_user(
                database_session=database_session,
                username=arguments.username,
                password=password,
            )

        except (
            AdminValidationError,
            AdminUsernameAlreadyExistsError,
        ) as error:
            print(f"Error: {error}")
            return 1

        except SQLAlchemyError:
            print(
                "Error: Administrator could not be saved "
                "because of a database error."
            )
            return 1

    print(
        f"Administrator '{admin_user.username}' "
        f"created successfully with ID {admin_user.id}."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())