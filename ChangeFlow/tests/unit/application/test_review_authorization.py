from datetime import UTC, datetime

from changeflow.application.ports.current_user_role_store import CurrentUser
from changeflow.application.ports.request_access_policy import RequestAccessPolicy
from changeflow.domain.change_requests.entities import ChangeRequest
from changeflow.domain.change_requests.enums import ChangeRequestStatus, Role
from changeflow.domain.change_requests.values import ChangeRequestContent


def request_for(owner: str, status: ChangeRequestStatus) -> ChangeRequest:
    request = ChangeRequest.create(
        owner,
        ChangeRequestContent("title", "detail", "reason"),
        datetime.now(UTC),
    )
    request.status = status
    return request


def test_visibility_rules_for_requester_reviewer_and_prior_reviewer() -> None:
    policy = RequestAccessPolicy()
    request = request_for("requester-1", ChangeRequestStatus.PENDING_REVIEW)

    assert policy.can_view(
        CurrentUser("requester-1", frozenset({Role.REQUESTER})), request
    )
    assert policy.can_view(
        CurrentUser("reviewer-1", frozenset({Role.REVIEWER})), request
    )
    assert not policy.can_view(
        CurrentUser("requester-2", frozenset({Role.REQUESTER})), request
    )

    request.status = ChangeRequestStatus.APPROVED
    request.prior_reviewer_ids.add("reviewer-1")
    assert policy.can_view(
        CurrentUser("reviewer-1", frozenset({Role.REVIEWER})), request
    )
    assert not policy.can_view(
        CurrentUser("reviewer-2", frozenset({Role.REVIEWER})), request
    )
