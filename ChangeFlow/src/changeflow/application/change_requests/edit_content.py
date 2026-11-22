from uuid import UUID

from changeflow.application.errors import (
    AuthorizationDeniedError,
    ValidationFailedError,
)
from changeflow.application.errors import (
    InvalidWorkflowError as ApplicationInvalidWorkflowError,
)
from changeflow.application.ports.current_user_role_store import CurrentUser
from changeflow.application.ports.unit_of_work import UnitOfWork
from changeflow.domain.change_requests.entities import ChangeRequest
from changeflow.domain.change_requests.enums import Role
from changeflow.domain.change_requests.errors import (
    DomainValidationError,
)
from changeflow.domain.change_requests.errors import (
    InvalidWorkflowError as DomainInvalidWorkflowError,
)
from changeflow.domain.change_requests.values import ChangeRequestContent

from .common import load_request, require_role, require_version


def edit_change_request_content(
    uow: UnitOfWork,
    user: CurrentUser,
    request_id: UUID,
    expected_version: UUID,
    content: ChangeRequestContent,
) -> ChangeRequest:
    require_role(user, Role.REQUESTER)
    request = load_request(uow, request_id)
    if request.requester_id != user.id:
        raise AuthorizationDeniedError("only the request owner may edit content")
    require_version(request, expected_version)
    try:
        request.edit_content(user.id, user.roles, content)
        saved = uow.requests.save(request)
        uow.commit(request_id)
        return saved
    except DomainValidationError as exc:
        uow.rollback()
        raise ValidationFailedError(str(exc)) from exc
    except DomainInvalidWorkflowError as exc:
        uow.rollback()
        raise ApplicationInvalidWorkflowError(str(exc)) from exc
    except Exception:
        uow.rollback()
        raise
