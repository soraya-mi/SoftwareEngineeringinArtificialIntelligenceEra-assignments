import pytest
from sqlalchemy.orm import Session, sessionmaker

from changeflow.application.change_requests.approve import approve_change_request
from changeflow.application.change_requests.create import create_change_request
from changeflow.application.change_requests.submit import submit_change_request
from changeflow.application.errors import ConcurrencyConflictError
from changeflow.application.ports.current_user_role_store import CurrentUser
from changeflow.domain.change_requests.enums import Role
from changeflow.domain.change_requests.values import ChangeRequestContent
from changeflow.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork


def test_competing_review_decisions_allow_exactly_one(
    session_factory: sessionmaker[Session],
    seed_user,
) -> None:
    seed_user("requester-1", {Role.REQUESTER})
    seed_user("reviewer-1", {Role.REVIEWER})
    seed_user("reviewer-2", {Role.REVIEWER})
    requester = CurrentUser("requester-1", frozenset({Role.REQUESTER}))
    create_uow = SqlAlchemyUnitOfWork(session_factory)
    created = create_change_request(
        create_uow, requester, ChangeRequestContent("title", "detail", "reason")
    )
    create_uow.close()
    submit_uow = SqlAlchemyUnitOfWork(session_factory)
    pending = submit_change_request(
        submit_uow, requester, created.id, created.version
    )
    submit_uow.close()

    first = SqlAlchemyUnitOfWork(session_factory)
    second = SqlAlchemyUnitOfWork(session_factory)
    reviewer1 = CurrentUser("reviewer-1", frozenset({Role.REVIEWER}))
    reviewer2 = CurrentUser("reviewer-2", frozenset({Role.REVIEWER}))
    assert first.requests.get(pending.id) is not None
    assert second.requests.get(pending.id) is not None
    approve_change_request(first, reviewer1, pending.id, pending.version)
    first.close()
    with pytest.raises(ConcurrencyConflictError):
        approve_change_request(second, reviewer2, pending.id, pending.version)
    second.close()

    verify = SqlAlchemyUnitOfWork(session_factory)
    persisted = verify.requests.get(pending.id)
    assert persisted is not None and persisted.status.value == "Approved"
    verify.close()
