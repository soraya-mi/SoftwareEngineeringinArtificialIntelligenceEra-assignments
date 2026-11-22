import pytest
from sqlalchemy.orm import Session, sessionmaker

from changeflow.application.change_requests.create import create_change_request
from changeflow.application.change_requests.edit_content import (
    edit_change_request_content,
)
from changeflow.application.errors import ConcurrencyConflictError
from changeflow.application.ports.current_user_role_store import CurrentUser
from changeflow.domain.change_requests.enums import Role
from changeflow.domain.change_requests.values import ChangeRequestContent
from changeflow.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork


def test_competing_content_updates_allow_exactly_one(
    session_factory: sessionmaker[Session],
    seed_user,
) -> None:
    seed_user("requester-1", {Role.REQUESTER})
    user = CurrentUser("requester-1", frozenset({Role.REQUESTER}))
    create_uow = SqlAlchemyUnitOfWork(session_factory)
    created = create_change_request(
        create_uow, user, ChangeRequestContent("title", "detail", "reason")
    )
    create_uow.close()

    first = SqlAlchemyUnitOfWork(session_factory)
    second = SqlAlchemyUnitOfWork(session_factory)
    first_version = first.requests.get(created.id).version  # type: ignore[union-attr]
    second_version = second.requests.get(created.id).version  # type: ignore[union-attr]
    assert first_version == second_version

    edit_change_request_content(
        first,
        user,
        created.id,
        first_version,
        ChangeRequestContent("first", "detail", "reason"),
    )
    first.close()

    with pytest.raises(ConcurrencyConflictError):
        edit_change_request_content(
            second,
            user,
            created.id,
            second_version,
            ChangeRequestContent("second", "detail", "reason"),
        )
    second.close()

    verify = SqlAlchemyUnitOfWork(session_factory)
    persisted = verify.requests.get(created.id)
    assert persisted is not None and persisted.content.title == "first"
    verify.close()
