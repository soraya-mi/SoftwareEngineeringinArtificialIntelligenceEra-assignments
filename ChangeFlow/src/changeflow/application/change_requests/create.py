from datetime import UTC, datetime

from changeflow.application.ports.current_user_role_store import CurrentUser
from changeflow.application.ports.unit_of_work import UnitOfWork
from changeflow.domain.change_requests.entities import ChangeRequest
from changeflow.domain.change_requests.enums import Role
from changeflow.domain.change_requests.values import ChangeRequestContent

from .common import require_role


def create_change_request(
    uow: UnitOfWork,
    user: CurrentUser,
    content: ChangeRequestContent,
) -> ChangeRequest:
    require_role(user, Role.REQUESTER)
    request = ChangeRequest.create(user.id, content, datetime.now(UTC))
    try:
        saved = uow.requests.save(request)
        uow.commit(saved.id)
        return saved
    except Exception:
        uow.rollback()
        raise
