from enum import StrEnum


class ChangeRequestStatus(StrEnum):
    DRAFT = "Draft"
    PENDING_REVIEW = "PendingReview"
    APPROVED = "Approved"
    CHANGES_REQUESTED = "ChangesRequested"


class ChangeRequestAction(StrEnum):
    SUBMIT = "Submit"
    APPROVE = "Approve"
    REQUEST_CHANGES = "RequestChanges"


class Role(StrEnum):
    REQUESTER = "Requester"
    REVIEWER = "Reviewer"
