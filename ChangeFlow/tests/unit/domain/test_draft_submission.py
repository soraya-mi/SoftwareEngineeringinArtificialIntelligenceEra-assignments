from datetime import UTC, datetime

import pytest

from changeflow.domain.change_requests.entities import ChangeRequest
from changeflow.domain.change_requests.enums import (
    ChangeRequestAction,
    ChangeRequestStatus,
    Role,
)
from changeflow.domain.change_requests.errors import InvalidWorkflowError
from changeflow.domain.change_requests.values import ChangeRequestContent


@pytest.mark.workflow
def test_draft_owner_can_submit_and_snapshot_content() -> None:
    request = ChangeRequest.create(
        "requester-1",
        ChangeRequestContent("title", "detail", "reason"),
        datetime.now(UTC),
    )
    transition = request.submit(
        "requester-1",
        frozenset({Role.REQUESTER}),
        datetime.now(UTC),
        None,
    )
    assert transition.action is ChangeRequestAction.SUBMIT
    assert transition.content_snapshot == request.content
    assert request.status is ChangeRequestStatus.PENDING_REVIEW


@pytest.mark.workflow
def test_pending_request_cannot_be_submitted_again() -> None:
    request = ChangeRequest.create(
        "requester-1",
        ChangeRequestContent("title", "detail", "reason"),
        datetime.now(UTC),
    )
    request.status = ChangeRequestStatus.PENDING_REVIEW
    with pytest.raises(InvalidWorkflowError):
        request.submit(
            "requester-1",
            frozenset({Role.REQUESTER}),
            datetime.now(UTC),
            None,
        )
