from datetime import UTC, datetime
from uuid import UUID, uuid4

from changeflow.application.errors import (
    AuthorizationDeniedError,
)
from changeflow.application.errors import (
    InvalidWorkflowError as ApplicationInvalidWorkflowError,
)
from changeflow.application.ports.current_user_role_store import CurrentUser
from changeflow.application.ports.unit_of_work import UnitOfWork
from changeflow.domain.change_requests.entities import (
    ChangeRequest,
    ChangeRequestRevision,
    ChangeRequestTransition,
)
from changeflow.domain.change_requests.enums import ChangeRequestStatus, Role
from changeflow.domain.change_requests.errors import (
    InvalidWorkflowError as DomainInvalidWorkflowError,
)

from .common import load_request, require_role, require_version


def submit_change_request(
    uow: UnitOfWork,
    user: CurrentUser,
    request_id: UUID,
    expected_version: UUID,
) -> ChangeRequest:
    require_role(user, Role.REQUESTER)
    request = load_request(uow, request_id)
    if request.requester_id != user.id:
        raise AuthorizationDeniedError("only the request owner may submit")
    require_version(request, expected_version)

    reviewed_content = None
    if request.status is ChangeRequestStatus.CHANGES_REQUESTED:
        if request.latest_reviewed_revision_id is None:
            raise ApplicationInvalidWorkflowError("no reviewed revision is available")
        revision = uow.requests.get_revision(request.latest_reviewed_revision_id)
        if revision is None:
            raise ApplicationInvalidWorkflowError("reviewed revision is unavailable")
        reviewed_content = revision.content

    try:
        now = datetime.now(UTC)
        spec = request.submit(user.id, user.roles, now, reviewed_content)
        saved = uow.requests.save(request)
        revision = ChangeRequestRevision(
            id=uuid4(),
            change_request_id=request.id,
            revision_number=uow.requests.next_revision_number(request.id),
            content=request.content,
            submitted_at=now,
            submitted_by=user.id,
        )
        transition = ChangeRequestTransition(
            id=uuid4(),
            change_request_id=request.id,
            actor_id=user.id,
            action=spec.action,
            from_status=spec.from_status,
            to_status=spec.to_status,
            occurred_at=spec.occurred_at,
            comment=spec.comment,
            reviewed_revision_id=spec.reviewed_revision_id,
        )
        uow.requests.add_revision(revision)
        uow.requests.add_transition(transition)
        uow.commit(request_id)
        return saved
    except DomainInvalidWorkflowError as exc:
        uow.rollback()
        raise ApplicationInvalidWorkflowError(str(exc)) from exc
    except Exception:
        uow.rollback()
        raise
