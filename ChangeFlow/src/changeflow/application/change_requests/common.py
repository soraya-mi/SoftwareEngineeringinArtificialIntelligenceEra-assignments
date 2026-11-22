from uuid import UUID

from changeflow.application.errors import (
    AuthorizationDeniedError,
    ConcurrencyConflictError,
    NotFoundError,
)
from changeflow.application.ports.current_user_role_store import CurrentUser
from changeflow.application.ports.unit_of_work import UnitOfWork
from changeflow.domain.change_requests.entities import ChangeRequest
from changeflow.domain.change_requests.enums import Role


def require_role(user: CurrentUser, role: Role) -> None:
    if role not in user.roles:
        raise AuthorizationDeniedError(f"{role.value} role is required")


def require_any_role(user: CurrentUser, *roles: Role) -> None:
    if not any(role in user.roles for role in roles):
        raise AuthorizationDeniedError("an authorized ChangeFlow role is required")


def load_request(uow: UnitOfWork, request_id: UUID) -> ChangeRequest:
    request = uow.requests.get(request_id)
    if request is None:
        raise NotFoundError("change request was not found")
    return request


def require_version(request: ChangeRequest, expected_version: UUID) -> None:
    if request.version != expected_version:
        raise ConcurrencyConflictError(
            "the request was changed by another operation",
            current_version=request.version,
        )
