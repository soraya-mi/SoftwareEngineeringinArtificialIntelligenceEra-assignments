from datetime import UTC, datetime

import pytest

from changeflow.domain.change_requests.entities import ChangeRequest
from changeflow.domain.change_requests.enums import ChangeRequestStatus, Role
from changeflow.domain.change_requests.errors import (
    DomainValidationError,
    InvalidWorkflowError,
)
from changeflow.domain.change_requests.values import ChangeRequestContent


@pytest.mark.workflow
def test_create_trims_content_and_starts_in_draft() -> None:
    request = ChangeRequest.create(
        "requester-1",
        ChangeRequestContent.create(" title ", " description ", " reason "),
        datetime.now(UTC),
    )

    assert request.status is ChangeRequestStatus.DRAFT
    assert request.content == ChangeRequestContent("title", "description", "reason")
    assert request.requester_id == "requester-1"


@pytest.mark.workflow
def test_owner_can_edit_but_other_user_cannot() -> None:
    request = ChangeRequest.create(
        "requester-1",
        ChangeRequestContent("before", "detail", "reason"),
        datetime.now(UTC),
    )
    request.edit_content(
        "requester-1",
        frozenset({Role.REQUESTER}),
        ChangeRequestContent("after", "new detail", "new reason"),
    )
    assert request.content.title == "after"

    with pytest.raises(InvalidWorkflowError):
        request.edit_content(
            "requester-2",
            frozenset({Role.REQUESTER}),
            ChangeRequestContent("hacked", "detail", "reason"),
        )


@pytest.mark.workflow
def test_approved_request_cannot_be_edited() -> None:
    request = ChangeRequest.create(
        "requester-1",
        ChangeRequestContent("title", "detail", "reason"),
        datetime.now(UTC),
    )
    request.status = ChangeRequestStatus.APPROVED
    with pytest.raises(InvalidWorkflowError):
        request.edit_content(
            "requester-1",
            frozenset({Role.REQUESTER}),
            ChangeRequestContent("new", "detail", "reason"),
        )


@pytest.mark.workflow
def test_content_rejects_whitespace_only() -> None:
    with pytest.raises(DomainValidationError):
        ChangeRequestContent.create(" ", "detail", "reason")
