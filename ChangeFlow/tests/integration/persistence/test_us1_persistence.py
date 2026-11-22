from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from changeflow.application.change_requests.create import create_change_request
from changeflow.application.change_requests.submit import submit_change_request
from changeflow.application.ports.current_user_role_store import CurrentUser
from changeflow.domain.change_requests.enums import Role
from changeflow.domain.change_requests.values import ChangeRequestContent
from changeflow.infrastructure.persistence.mappings import (
    ChangeRequestRevisionModel,
    ChangeRequestTransitionModel,
)
from changeflow.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork


def test_create_edit_submit_persist_revision_and_transition(
    session_factory: sessionmaker[Session],
    seed_user,
) -> None:
    seed_user("requester-1", {Role.REQUESTER})
    user = CurrentUser("requester-1", frozenset({Role.REQUESTER}))
    uow = SqlAlchemyUnitOfWork(session_factory)
    created = create_change_request(
        uow,
        user,
        ChangeRequestContent(" title ", " detail ", " reason "),
    )
    uow.close()

    submit_uow = SqlAlchemyUnitOfWork(session_factory)
    submitted = submit_change_request(
        submit_uow,
        user,
        created.id,
        created.version,
    )
    submit_uow.close()
    assert submitted.content.title == "title"

    with session_factory() as session:
        revisions = session.scalar(
            select(func.count()).select_from(ChangeRequestRevisionModel)
        )
        transitions = session.scalar(
            select(func.count()).select_from(ChangeRequestTransitionModel)
        )
    assert revisions == 1
    assert transitions == 1
