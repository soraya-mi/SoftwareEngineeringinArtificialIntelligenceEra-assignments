from datetime import UTC, datetime
from uuid import uuid4

import pytest

from changeflow.domain.change_requests.entities import ChangeRequest
from changeflow.domain.change_requests.enums import ChangeRequestStatus, Role
from changeflow.domain.change_requests.errors import (
    DomainValidationError,
    SelfApprovalForbiddenError,
)
from changeflow.domain.change_requests.values import ChangeRequestContent


def pending_request(owner: str = "requester-1") -> ChangeRequest:
    request = ChangeRequest.create(
        owner,
        ChangeRequestContent("title", "detail", "reason"),
        datetime.now(UTC),
    )
    request.status = ChangeRequestStatus.PENDING_REVIEW
    return request


@pytest.mark.workflow
def test_other_reviewer_can_approve() -> None:
    request = pending_request()
    request.approve("reviewer-1", frozenset({Role.REVIEWER}), datetime.now(UTC))
    assert request.status is ChangeRequestStatus.APPROVED
    assert "reviewer-1" in request.prior_reviewer_ids


@pytest.mark.workflow
def test_dual_role_owner_cannot_self_approve() -> None:
    request = pending_request()
    with pytest.raises(SelfApprovalForbiddenError):
        request.approve(
            "requester-1",
            frozenset({Role.REQUESTER, Role.REVIEWER}),
            datetime.now(UTC),
        )


@pytest.mark.workflow
def test_owner_may_request_changes_on_own_request_and_comment_is_unchanged() -> None:
    request = pending_request()
    revision_id = uuid4()
    transition = request.request_changes(
        "requester-1",
        frozenset({Role.REQUESTER, Role.REVIEWER}),
        "  explain the impact  ",
        revision_id,
        datetime.now(UTC),
    )
    assert request.status is ChangeRequestStatus.CHANGES_REQUESTED
    assert transition.comment == "  explain the impact  "
    assert transition.reviewed_revision_id == revision_id


@pytest.mark.workflow
def test_request_changes_requires_comment() -> None:
    request = pending_request()
    with pytest.raises(DomainValidationError):
        request.request_changes(
            "reviewer-1",
            frozenset({Role.REVIEWER}),
            "   ",
            uuid4(),
            datetime.now(UTC),
        )
