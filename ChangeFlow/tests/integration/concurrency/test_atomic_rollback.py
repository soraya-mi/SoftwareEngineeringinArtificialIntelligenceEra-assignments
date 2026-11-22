import pytest
from sqlalchemy.orm import Session, sessionmaker

from changeflow.application.change_requests.create import create_change_request
from changeflow.application.change_requests.request_changes import request_changes
from changeflow.application.change_requests.submit import submit_change_request
from changeflow.application.ports.current_user_role_store import CurrentUser
from changeflow.domain.change_requests.enums import Role
from changeflow.domain.change_requests.values import ChangeRequestContent
from changeflow.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork


def test_transition_failure_rolls_back_request_state(
    session_factory: sessionmaker[Session],
    seed_user,
) -> None:
    seed_user("requester-1", {Role.REQUESTER})
    seed_user("reviewer-1", {Role.REVIEWER})
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

    reviewer = CurrentUser("reviewer-1", frozenset({Role.REVIEWER}))
    uow = SqlAlchemyUnitOfWork(session_factory)

    def fail_transition(_: object) -> None:
        raise RuntimeError("forced transition failure")

    uow.requests.add_transition = fail_transition  # type: ignore[method-assign]
    with pytest.raises(RuntimeError):
        request_changes(
            uow,
            reviewer,
            pending.id,
            pending.version,
            "feedback",
        )
    uow.close()

    verify = SqlAlchemyUnitOfWork(session_factory)
    persisted = verify.requests.get(pending.id)
    assert persisted is not None and persisted.status.value == "PendingReview"
    verify.close()
