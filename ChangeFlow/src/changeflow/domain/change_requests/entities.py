from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from .enums import ChangeRequestAction, ChangeRequestStatus, Role
from .errors import (
    DomainValidationError,
    InvalidWorkflowError,
    SelfApprovalForbiddenError,
)
from .values import ChangeRequestContent, validate_review_comment


@dataclass(frozen=True)
class TransitionSpec:
    action: ChangeRequestAction
    from_status: ChangeRequestStatus
    to_status: ChangeRequestStatus
    occurred_at: datetime
    content_snapshot: ChangeRequestContent | None = None
    comment: str | None = None
    reviewed_revision_id: UUID | None = None


@dataclass(frozen=True)
class ChangeRequestRevision:
    id: UUID
    change_request_id: UUID
    revision_number: int
    content: ChangeRequestContent
    submitted_at: datetime
    submitted_by: str


@dataclass(frozen=True)
class ChangeRequestTransition:
    id: UUID
    change_request_id: UUID
    actor_id: str
    action: ChangeRequestAction
    from_status: ChangeRequestStatus
    to_status: ChangeRequestStatus
    occurred_at: datetime
    comment: str | None
    reviewed_revision_id: UUID | None


@dataclass
class ChangeRequest:
    id: UUID
    requester_id: str
    content: ChangeRequestContent
    status: ChangeRequestStatus
    version: UUID
    latest_reviewed_revision_id: UUID | None
    created_at: datetime
    updated_at: datetime
    prior_reviewer_ids: set[str] = field(default_factory=set)

    @classmethod
    def create(
        cls,
        requester_id: str,
        content: ChangeRequestContent,
        now: datetime,
        *,
        request_id: UUID | None = None,
    ) -> "ChangeRequest":
        return cls(
            id=request_id or uuid4(),
            requester_id=requester_id,
            content=content,
            status=ChangeRequestStatus.DRAFT,
            version=uuid4(),
            latest_reviewed_revision_id=None,
            created_at=now,
            updated_at=now,
        )

    def edit_content(
        self,
        actor_id: str,
        roles: frozenset[Role],
        content: ChangeRequestContent,
    ) -> None:
        self._require_owner_requester(actor_id, roles)
        if self.status not in {ChangeRequestStatus.DRAFT, ChangeRequestStatus.CHANGES_REQUESTED}:
            raise InvalidWorkflowError(f"content cannot be edited from {self.status.value}")
        self.content = content

    def submit(
        self,
        actor_id: str,
        roles: frozenset[Role],
        now: datetime,
        reviewed_content: ChangeRequestContent | None,
    ) -> TransitionSpec:
        self._require_owner_requester(actor_id, roles)
        if self.status not in {
            ChangeRequestStatus.DRAFT,
            ChangeRequestStatus.CHANGES_REQUESTED,
        }:
            raise InvalidWorkflowError(f"request cannot be submitted from {self.status.value}")
        if self.status is ChangeRequestStatus.CHANGES_REQUESTED:
            if reviewed_content is None:
                raise InvalidWorkflowError("reviewed content is unavailable")
            if reviewed_content == self.content:
                raise InvalidWorkflowError("at least one content field must change")

        from_status = self.status
        self.status = ChangeRequestStatus.PENDING_REVIEW
        self.updated_at = now
        return TransitionSpec(
            action=ChangeRequestAction.SUBMIT,
            from_status=from_status,
            to_status=self.status,
            occurred_at=now,
            content_snapshot=self.content,
        )

    def approve(
        self,
        actor_id: str,
        roles: frozenset[Role],
        now: datetime,
    ) -> TransitionSpec:
        if Role.REVIEWER not in roles:
            raise InvalidWorkflowError("Reviewer role is required")
        if self.status is not ChangeRequestStatus.PENDING_REVIEW:
            raise InvalidWorkflowError(f"request cannot be approved from {self.status.value}")
        if actor_id == self.requester_id:
            raise SelfApprovalForbiddenError("request owners cannot approve their own requests")

        from_status = self.status
        self.status = ChangeRequestStatus.APPROVED
        self.updated_at = now
        self.prior_reviewer_ids.add(actor_id)
        return TransitionSpec(
            action=ChangeRequestAction.APPROVE,
            from_status=from_status,
            to_status=self.status,
            occurred_at=now,
        )

    def request_changes(
        self,
        actor_id: str,
        roles: frozenset[Role],
        comment: str,
        reviewed_revision_id: UUID | None,
        now: datetime,
    ) -> TransitionSpec:
        if Role.REVIEWER not in roles:
            raise InvalidWorkflowError("Reviewer role is required")
        if self.status is not ChangeRequestStatus.PENDING_REVIEW:
            raise InvalidWorkflowError(
                f"changes cannot be requested from {self.status.value}"
            )
        if reviewed_revision_id is None:
            raise InvalidWorkflowError("no submitted revision is available for review")

        original_comment = validate_review_comment(comment)
        from_status = self.status
        self.status = ChangeRequestStatus.CHANGES_REQUESTED
        self.latest_reviewed_revision_id = reviewed_revision_id
        self.updated_at = now
        self.prior_reviewer_ids.add(actor_id)
        return TransitionSpec(
            action=ChangeRequestAction.REQUEST_CHANGES,
            from_status=from_status,
            to_status=self.status,
            occurred_at=now,
            comment=original_comment,
            reviewed_revision_id=reviewed_revision_id,
        )

    def ensure_editable_from_current_state(self) -> None:
        if self.status is ChangeRequestStatus.APPROVED:
            raise InvalidWorkflowError("approved requests are immutable")
        if not self.content.title or not self.content.description or not self.content.reason:
            raise DomainValidationError("request content is incomplete")

    def _require_owner_requester(self, actor_id: str, roles: frozenset[Role]) -> None:
        if Role.REQUESTER not in roles:
            raise InvalidWorkflowError("Requester role is required")
        if actor_id != self.requester_id:
            raise InvalidWorkflowError("only the request owner may perform this action")
