from changeflow.domain.change_requests.entities import ChangeRequest
from changeflow.domain.change_requests.enums import ChangeRequestStatus, Role

from .current_user_role_store import CurrentUser


class RequestAccessPolicy:
    def can_view(self, user: CurrentUser, request: ChangeRequest) -> bool:
        if request.requester_id == user.id and Role.REQUESTER in user.roles:
            return True
        if Role.REVIEWER not in user.roles:
            return False
        if (
            request.status is ChangeRequestStatus.PENDING_REVIEW
            and request.requester_id != user.id
        ):
            return True
        return user.id in request.prior_reviewer_ids
