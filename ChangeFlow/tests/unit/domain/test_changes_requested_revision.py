from datetime import UTC, datetime
from uuid import uuid4

import pytest

from changeflow.domain.change_requests.entities import ChangeRequest
from changeflow.domain.change_requests.enums import ChangeRequestStatus, Role
from changeflow.domain.change_requests.errors import InvalidWorkflowError
from changeflow.domain.change_requests.values import ChangeRequestContent


def changed_request() -> ChangeRequest:
    request = ChangeRequest.create(
        "requester-1",
        ChangeRequestContent("title", "detail", "reason"),
        datetime.now(UTC),
    )
    request.status = ChangeRequestStatus.CHANGES_REQUESTED
    request.latest_reviewed_revision_id = uuid4()
    return request


@pytest.mark.workflow
def test_unchanged_content_cannot_resubmit() -> None:
    request = changed_request()
    with pytest.raises(InvalidWorkflowError):
        request.submit(
            "requester-1",
            frozenset({Role.REQUESTER}),
            datetime.now(UTC),
            request.content,
        )


@pytest.mark.workflow
def test_changed_content_can_resubmit() -> None:
    request = changed_request()
    request.edit_content(
        "requester-1",
        frozenset({Role.REQUESTER}),
        ChangeRequestContent("new title", "detail", "reason"),
    )
    transition = request.submit(
        "requester-1",
        frozenset({Role.REQUESTER}),
        datetime.now(UTC),
        ChangeRequestContent("title", "detail", "reason"),
    )
    assert transition.to_status is ChangeRequestStatus.PENDING_REVIEW
