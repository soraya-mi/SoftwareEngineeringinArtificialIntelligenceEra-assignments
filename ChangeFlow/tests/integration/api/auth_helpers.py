from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from changeflow.api.dependencies import get_current_user
from changeflow.application.ports.current_user_role_store import CurrentUser
from changeflow.domain.change_requests.enums import Role
from changeflow.infrastructure.persistence.mappings import (
    UserAccountModel,
    UserRoleAssignmentModel,
)


@contextmanager
def client_for_user(
    app: object,
    user_id: str,
    roles: set[Role] | frozenset[Role],
) -> Iterator[TestClient]:
    user = CurrentUser(id=user_id, roles=frozenset(roles))
    now = datetime.now(UTC)
    with app.state.session_factory() as session:  # type: ignore[attr-defined]
        account = session.get(UserAccountModel, user_id)
        if account is None:
            account = UserAccountModel(
                id=user_id,
                is_active=True,
                created_at=now,
                updated_at=now,
            )
            session.add(account)
        else:
            account.is_active = True
            account.updated_at = now
        session.query(UserRoleAssignmentModel).filter_by(user_id=user_id).delete()
        for role in roles:
            session.add(UserRoleAssignmentModel(user_id=user_id, role=role.value))
        session.commit()
    previous = app.dependency_overrides.get(get_current_user)  # type: ignore[attr-defined]
    app.dependency_overrides[get_current_user] = lambda: user  # type: ignore[attr-defined]
    try:
        with TestClient(app) as client:  # type: ignore[arg-type]
            yield client
    finally:
        if previous is None:
            app.dependency_overrides.pop(get_current_user, None)  # type: ignore[attr-defined]
        else:
            app.dependency_overrides[get_current_user] = previous  # type: ignore[attr-defined]


def etag(response_json: dict[str, object]) -> str:
    return f'"{response_json["version"]}"'
