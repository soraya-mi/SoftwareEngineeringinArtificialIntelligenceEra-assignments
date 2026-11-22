from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from changeflow.application.ports.current_user_role_store import CurrentUser
from changeflow.domain.change_requests.enums import Role
from changeflow.infrastructure.persistence.mappings import (
    UserAccountModel,
    UserRoleAssignmentModel,
)


class SqlAlchemyCurrentUserRoleStore:
    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def get(self, user_id: str) -> CurrentUser | None:
        with self._session_factory() as session:
            user = session.get(UserAccountModel, user_id)
            if user is None or not user.is_active:
                return None
            roles = session.scalars(
                select(UserRoleAssignmentModel.role).where(
                    UserRoleAssignmentModel.user_id == user_id
                )
            ).all()
            return CurrentUser(id=user.id, roles=frozenset(Role(role) for role in roles))
