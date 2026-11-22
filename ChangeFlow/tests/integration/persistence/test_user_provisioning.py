from sqlalchemy.orm import Session, sessionmaker

from changeflow.cli.provision_user import provision_user
from changeflow.domain.change_requests.enums import Role
from changeflow.infrastructure.auth.current_user_role_store import (
    SqlAlchemyCurrentUserRoleStore,
)


def test_provision_dual_roles_revoke_and_replace_duplicate_roles(
    session_factory: sessionmaker[Session],
) -> None:
    provision_user(session_factory, "user-1", {Role.REQUESTER, Role.REVIEWER})
    provision_user(session_factory, "user-1", {Role.REQUESTER, Role.REVIEWER})
    store = SqlAlchemyCurrentUserRoleStore(session_factory)
    assert store.get("user-1") == type(store.get("user-1"))(
        id="user-1",
        roles=frozenset({Role.REQUESTER, Role.REVIEWER}),
    )

    provision_user(session_factory, "user-1", {Role.REQUESTER})
    current = store.get("user-1")
    assert current is not None
    assert current.roles == frozenset({Role.REQUESTER})

    provision_user(session_factory, "user-1", set(), active=False)
    assert store.get("user-1") is None
