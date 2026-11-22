from uuid import UUID

from changeflow.application.errors import AuthorizationDeniedError
from changeflow.application.ports.current_user_role_store import CurrentUser
from changeflow.application.ports.request_access_policy import RequestAccessPolicy
from changeflow.application.ports.unit_of_work import UnitOfWork
from changeflow.domain.change_requests.entities import ChangeRequest, ChangeRequestTransition
from changeflow.domain.change_requests.enums import Role

from .common import load_request, require_any_role


def list_visible_change_requests(
    uow: UnitOfWork,
    user: CurrentUser,
) -> list[ChangeRequest]:
    require_any_role(user, Role.REQUESTER, Role.REVIEWER)
    policy = RequestAccessPolicy()
    return [
        request
        for request in uow.requests.list_all()
        if policy.can_view(user, request)
    ]


def get_visible_change_request(
    uow: UnitOfWork,
    user: CurrentUser,
    request_id: UUID,
) -> ChangeRequest:
    require_any_role(user, Role.REQUESTER, Role.REVIEWER)
    request = load_request(uow, request_id)
    if not RequestAccessPolicy().can_view(user, request):
        raise AuthorizationDeniedError("change request is not visible to this user")
    return request


def get_change_request_history(
    uow: UnitOfWork,
    user: CurrentUser,
    request_id: UUID,
) -> list[ChangeRequestTransition]:
    get_visible_change_request(uow, user, request_id)
    return uow.requests.list_transitions(request_id)
