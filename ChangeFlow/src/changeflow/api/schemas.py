from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from changeflow.domain.change_requests.entities import (
    ChangeRequest,
    ChangeRequestTransition,
)
from changeflow.domain.change_requests.enums import ChangeRequestStatus


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ContentRequest(ApiModel):
    title: str
    description: str
    reason: str

    @field_validator("title", "description", "reason")
    @classmethod
    def non_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty")
        return value


class CreateChangeRequestRequest(ContentRequest):
    pass


class UpdateChangeRequestContentRequest(ContentRequest):
    pass


class RequestChangesRequest(ApiModel):
    comment: str = Field(min_length=1)

    @field_validator("comment")
    @classmethod
    def non_blank_comment(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty")
        return value


class ChangeRequestResponse(ApiModel):
    id: UUID
    requesterId: str
    title: str
    description: str
    reason: str
    status: ChangeRequestStatus
    version: UUID
    createdAt: datetime
    updatedAt: datetime

    @classmethod
    def from_domain(cls, request: ChangeRequest) -> "ChangeRequestResponse":
        return cls(
            id=request.id,
            requesterId=request.requester_id,
            title=request.content.title,
            description=request.content.description,
            reason=request.content.reason,
            status=request.status,
            version=request.version,
            createdAt=request.created_at,
            updatedAt=request.updated_at,
        )


class ChangeRequestListResponse(ApiModel):
    items: list[ChangeRequestResponse]


class ChangeRequestTransitionResponse(ApiModel):
    id: UUID
    actorId: str
    action: str
    fromStatus: ChangeRequestStatus
    toStatus: ChangeRequestStatus
    comment: str | None = None
    reviewedRevisionId: UUID | None = None
    occurredAt: datetime

    @classmethod
    def from_domain(
        cls, transition: ChangeRequestTransition
    ) -> "ChangeRequestTransitionResponse":
        return cls(
            id=transition.id,
            actorId=transition.actor_id,
            action=transition.action.value,
            fromStatus=transition.from_status,
            toStatus=transition.to_status,
            comment=transition.comment,
            reviewedRevisionId=transition.reviewed_revision_id,
            occurredAt=transition.occurred_at,
        )


class ChangeRequestHistoryResponse(ApiModel):
    requestId: UUID
    items: list[ChangeRequestTransitionResponse]


class ErrorCode(StrEnum):
    AUTHENTICATION_REQUIRED = "AUTHENTICATION_REQUIRED"
    AUTHORIZATION_DENIED = "AUTHORIZATION_DENIED"
    SELF_APPROVAL_FORBIDDEN = "SELF_APPROVAL_FORBIDDEN"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    INVALID_WORKFLOW = "INVALID_WORKFLOW"
    CONCURRENCY_CONFLICT = "CONCURRENCY_CONFLICT"
    PRECONDITION_REQUIRED = "PRECONDITION_REQUIRED"
    DELETION_NOT_SUPPORTED = "DELETION_NOT_SUPPORTED"
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    HTTP_ERROR = "HTTP_ERROR"


class ProblemDetails(ApiModel):
    type: str = "about:blank"
    title: str
    status: int
    detail: str | None = None
    instance: str | None = None
    code: ErrorCode
    currentVersion: UUID | None = None
