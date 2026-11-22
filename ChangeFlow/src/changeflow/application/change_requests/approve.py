from datetime import UTC, datetime
from uuid import UUID, uuid4

from changeflow.application.errors import (
    InvalidWorkflowError as ApplicationInvalidWorkflowError,
)
from changeflow.application.errors import (
    SelfApprovalForbiddenError,
)
from changeflow.application.ports.current_user_role_store import CurrentUser
from changeflow.application.ports.unit_of_work import UnitOfWork
from changeflow.domain.change_requests.entities import ChangeRequest, ChangeRequestTransition
from changeflow.domain.change_requests.enums import Role
from changeflow.domain.change_requests.errors import (
    InvalidWorkflowError as DomainInvalidWorkflowError,
)
from changeflow.domain.change_requests.errors import (
    SelfApprovalForbiddenError as DomainSelfApprovalError,
)

from .common import load_request, require_role, require_version


def approve_change_request(
    uow: UnitOfWork,
    user: CurrentUser,
    request_id: UUID,
    expected_version: UUID,
) -> ChangeRequest:
    require_role(user, Role.REVIEWER)
    request = load_request(uow, request_id)
    require_version(request, expected_version)
    try:
        spec = request.approve(user.id, user.roles, datetime.now(UTC))
        saved = uow.requests.save(request)
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
        uow.requests.add_transition(transition)
        uow.commit(request_id)
        return saved
    except DomainSelfApprovalError as exc:
        uow.rollback()
        raise SelfApprovalForbiddenError(str(exc)) from exc
    except DomainInvalidWorkflowError as exc:
        uow.rollback()
        raise ApplicationInvalidWorkflowError(str(exc)) from exc
    except Exception:
        uow.rollback()
        raise
