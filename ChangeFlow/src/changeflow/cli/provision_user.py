import argparse
from collections.abc import Callable, Sequence
from datetime import UTC, datetime

from sqlalchemy import delete
from sqlalchemy.orm import Session

from changeflow.domain.change_requests.enums import Role
from changeflow.infrastructure.config import Settings
from changeflow.infrastructure.persistence.database import (
    create_database_engine,
    create_session_factory,
)
from changeflow.infrastructure.persistence.mappings import (
    UserAccountModel,
    UserRoleAssignmentModel,
)


def provision_user(
    session_factory: Callable[[], Session],
    user_id: str,
    roles: set[Role],
    *,
    active: bool = True,
) -> None:
    session = session_factory()
    try:
        now = datetime.now(UTC)
        user = session.get(UserAccountModel, user_id)
        if user is None:
            user = UserAccountModel(
                id=user_id,
                is_active=active,
                created_at=now,
                updated_at=now,
            )
            session.add(user)
        else:
            user.is_active = active
            user.updated_at = now
        session.execute(
            delete(UserRoleAssignmentModel).where(
                UserRoleAssignmentModel.user_id == user_id
            )
        )
        for role in sorted(roles, key=lambda item: item.value):
            session.add(UserRoleAssignmentModel(user_id=user_id, role=role.value))
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Provision a ChangeFlow user and roles")
    parser.add_argument("--user-id", required=True)
    parser.add_argument("--roles", required=True, help="Comma-separated Requester,Reviewer")
    args = parser.parse_args(argv)
    roles = {
        Role(value.strip())
        for value in str(args.roles).split(",")
        if value.strip()
    }
    settings = Settings()
    engine = create_database_engine(settings)
    provision_user(create_session_factory(engine), str(args.user_id), roles)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
