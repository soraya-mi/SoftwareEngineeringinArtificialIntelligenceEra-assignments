from sqlalchemy.orm import Session, sessionmaker

from changeflow.application.change_requests.create import create_change_request
from changeflow.application.change_requests.edit_content import (
    edit_change_request_content,
)
from changeflow.application.change_requests.request_changes import request_changes
from changeflow.application.change_requests.submit import submit_change_request
from changeflow.application.ports.current_user_role_store import CurrentUser
from changeflow.domain.change_requests.enums import Role
from changeflow.domain.change_requests.values import ChangeRequestContent
from changeflow.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork


def test_prior_reviewed_content_and_comment_survive_resubmission(
    session_factory: sessionmaker[Session],
    seed_user,
) -> None:
    seed_user("requester-1", {Role.REQUESTER})
    seed_user("reviewer-1", {Role.REVIEWER})
    requester = CurrentUser("requester-1", frozenset({Role.REQUESTER}))
    reviewer = CurrentUser("reviewer-1", frozenset({Role.REVIEWER}))

    first = SqlAlchemyUnitOfWork(session_factory)
    created = create_change_request(
        first, requester, ChangeRequestContent("before", "detail", "reason")
    )
    first.close()
    second = SqlAlchemyUnitOfWork(session_factory)
    pending = submit_change_request(second, requester, created.id, created.version)
    second.close()
    third = SqlAlchemyUnitOfWork(session_factory)
    changed = request_changes(
        third, reviewer, pending.id, pending.version, "Please revise impact"
    )
    third.close()
    fourth = SqlAlchemyUnitOfWork(session_factory)
    edited = edit_change_request_content(
        fourth,
        requester,
        changed.id,
        changed.version,
        ChangeRequestContent("after", "detail", "reason"),
    )
    fourth.close()
    fifth = SqlAlchemyUnitOfWork(session_factory)
    resubmitted = submit_change_request(
        fifth, requester, edited.id, edited.version
    )
    history = fifth.requests.list_transitions(resubmitted.id)
    latest_reviewed = fifth.requests.get_revision(
        changed.latest_reviewed_revision_id  # type: ignore[arg-type]
    )
    fifth.close()

    assert [item.action.value for item in history] == [
        "Submit",
        "RequestChanges",
        "Submit",
    ]
    assert latest_reviewed is not None
    assert latest_reviewed.content.title == "before"
    assert history[1].comment == "Please revise impact"
