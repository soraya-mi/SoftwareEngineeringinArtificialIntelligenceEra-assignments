import pytest
from sqlalchemy.orm import Session, sessionmaker

from changeflow.application.change_requests.approve import approve_change_request
from changeflow.application.change_requests.create import create_change_request
from changeflow.application.change_requests.request_changes import request_changes
from changeflow.application.change_requests.submit import submit_change_request
from changeflow.application.errors import ValidationFailedError
from changeflow.application.ports.current_user_role_store import CurrentUser
from changeflow.domain.change_requests.enums import Role
from changeflow.domain.change_requests.values import ChangeRequestContent
from changeflow.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork


def pending_request(
    session_factory: sessionmaker[Session],
) -> tuple[CurrentUser, object]:
    requester = CurrentUser("requester-1", frozenset({Role.REQUESTER}))
    uow = SqlAlchemyUnitOfWork(session_factory)
    created = create_change_request(
        uow, requester, ChangeRequestContent("title", "detail", "reason")
    )
    uow.close()
    submit_uow = SqlAlchemyUnitOfWork(session_factory)
    submitted = submit_change_request(
        submit_uow, requester, created.id, created.version
    )
    submit_uow.close()
    return requester, submitted


def test_request_changes_persists_original_comment_and_history(
    session_factory: sessionmaker[Session],
    seed_user,
) -> None:
    seed_user("requester-1", {Role.REQUESTER})
    seed_user("reviewer-1", {Role.REVIEWER})
    _, pending = pending_request(session_factory)
    reviewer = CurrentUser("reviewer-1", frozenset({Role.REVIEWER}))
    uow = SqlAlchemyUnitOfWork(session_factory)
    changed = request_changes(
        uow,
        reviewer,
        pending.id,  # type: ignore[attr-defined]
        pending.version,  # type: ignore[attr-defined]
        "  exact feedback  ",
    )
    history = uow.requests.list_transitions(changed.id)
    uow.close()
    assert changed.status.value == "ChangesRequested"
    assert history[-1].comment == "  exact feedback  "


def test_approval_is_persisted(
    session_factory: sessionmaker[Session],
    seed_user,
) -> None:
    seed_user("requester-1", {Role.REQUESTER})
    seed_user("reviewer-1", {Role.REVIEWER})
    _, pending = pending_request(session_factory)
    reviewer = CurrentUser("reviewer-1", frozenset({Role.REVIEWER}))
    uow = SqlAlchemyUnitOfWork(session_factory)
    approved = approve_change_request(
        uow,
        reviewer,
        pending.id,  # type: ignore[attr-defined]
        pending.version,  # type: ignore[attr-defined]
    )
    uow.close()
    assert approved.status.value == "Approved"


def test_blank_feedback_leaves_version_status_and_history_unchanged(
    session_factory: sessionmaker[Session],
    seed_user,
) -> None:
    seed_user("requester-1", {Role.REQUESTER})
    seed_user("reviewer-1", {Role.REVIEWER})
    _, pending = pending_request(session_factory)
    reviewer = CurrentUser("reviewer-1", frozenset({Role.REVIEWER}))
    uow = SqlAlchemyUnitOfWork(session_factory)
    with pytest.raises(ValidationFailedError):
        request_changes(
            uow,
            reviewer,
            pending.id,  # type: ignore[attr-defined]
            pending.version,  # type: ignore[attr-defined]
            "   ",
        )
    persisted = uow.requests.get(pending.id)  # type: ignore[attr-defined]
    history = uow.requests.list_transitions(pending.id)  # type: ignore[attr-defined]
    uow.close()
    assert persisted is not None
    assert persisted.version == pending.version  # type: ignore[attr-defined]
    assert persisted.status.value == "PendingReview"
    assert [item.action.value for item in history] == ["Submit"]
