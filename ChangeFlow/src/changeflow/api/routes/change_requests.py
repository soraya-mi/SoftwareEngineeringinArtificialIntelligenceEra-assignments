from typing import Any
from uuid import UUID

from fastapi import APIRouter, Response, status

from changeflow.api.dependencies import (
    CurrentUserDependency,
    ExpectedVersionDependency,
    UnitOfWorkDependency,
    quote_etag,
)
from changeflow.api.schemas import (
    ChangeRequestHistoryResponse,
    ChangeRequestListResponse,
    ChangeRequestResponse,
    ChangeRequestTransitionResponse,
    CreateChangeRequestRequest,
    ProblemDetails,
    RequestChangesRequest,
    UpdateChangeRequestContentRequest,
)
from changeflow.application.change_requests.approve import approve_change_request
from changeflow.application.change_requests.create import create_change_request
from changeflow.application.change_requests.edit_content import (
    edit_change_request_content,
)
from changeflow.application.change_requests.queries import (
    get_change_request_history,
    get_visible_change_request,
    list_visible_change_requests,
)
from changeflow.application.change_requests.request_changes import request_changes
from changeflow.application.change_requests.submit import submit_change_request
from changeflow.application.errors import DeletionNotSupportedError
from changeflow.domain.change_requests.values import ChangeRequestContent

router = APIRouter(prefix="/api/change-requests", tags=["Change Requests"])

_PROBLEM_CONTENT = {
    "application/problem+json": {
        "schema": {"$ref": "#/components/schemas/ProblemDetails"}
    }
}
_ERROR_DESCRIPTIONS = {
    400: "Invalid request content",
    401: "Authentication required",
    403: "Authorization denied",
    404: "Change Request not found",
    405: "Request deletion is not supported",
    409: "Invalid workflow or concurrency conflict",
    428: "If-Match precondition required",
}
_ETAG_HEADER = {
    "description": "Current Change Request concurrency token as a quoted UUID.",
    "schema": {"type": "string"},
}


def _responses(
    success_status: int,
    error_statuses: tuple[int, ...],
    *,
    etag: bool,
) -> dict[int | str, dict[str, Any]]:
    responses: dict[int | str, dict[str, Any]] = {
        status: {
            "model": ProblemDetails,
            "description": _ERROR_DESCRIPTIONS[status],
            "content": _PROBLEM_CONTENT,
        }
        for status in error_statuses
    }
    if etag:
        responses[success_status] = {"headers": {"ETag": _ETAG_HEADER}}
    return responses


def _response(
    request: object, response: Response
) -> ChangeRequestResponse:
    domain = request
    response.headers["ETag"] = quote_etag(domain.version)  # type: ignore[attr-defined]
    return ChangeRequestResponse.from_domain(domain)  # type: ignore[arg-type]


@router.get(
    "",
    response_model=ChangeRequestListResponse,
    operation_id="listVisibleChangeRequests",
    responses=_responses(200, (401, 403), etag=False),
)
def list_requests(
    user: CurrentUserDependency,
    uow: UnitOfWorkDependency,
) -> ChangeRequestListResponse:
    requests = list_visible_change_requests(uow, user)
    return ChangeRequestListResponse(
        items=[ChangeRequestResponse.from_domain(request) for request in requests]
    )


@router.post(
    "",
    response_model=ChangeRequestResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createChangeRequest",
    responses=_responses(201, (400, 401, 403), etag=True),
)
def create_request(
    payload: CreateChangeRequestRequest,
    response: Response,
    user: CurrentUserDependency,
    uow: UnitOfWorkDependency,
) -> ChangeRequestResponse:
    content = ChangeRequestContent.create(
        payload.title,
        payload.description,
        payload.reason,
    )
    request = create_change_request(uow, user, content)
    response.headers["Location"] = f"/api/change-requests/{request.id}"
    return _response(request, response)


@router.get(
    "/{request_id}",
    response_model=ChangeRequestResponse,
    operation_id="getChangeRequest",
    responses=_responses(200, (401, 403, 404), etag=True),
)
def get_request(
    request_id: UUID,
    response: Response,
    user: CurrentUserDependency,
    uow: UnitOfWorkDependency,
) -> ChangeRequestResponse:
    request = get_visible_change_request(uow, user, request_id)
    return _response(request, response)


@router.delete(
    "/{request_id}",
    status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
    operation_id="deleteChangeRequest",
    responses=_responses(405, (401, 405), etag=False),
)
def delete_request(
    request_id: UUID,
    user: CurrentUserDependency,
) -> None:
    del request_id, user
    raise DeletionNotSupportedError("change request deletion is not supported")


@router.put(
    "/{request_id}/content",
    response_model=ChangeRequestResponse,
    operation_id="updateChangeRequestContent",
    responses=_responses(200, (400, 401, 403, 404, 409, 428), etag=True),
)
def update_content(
    request_id: UUID,
    payload: UpdateChangeRequestContentRequest,
    response: Response,
    user: CurrentUserDependency,
    uow: UnitOfWorkDependency,
    expected_version: ExpectedVersionDependency,
) -> ChangeRequestResponse:
    content = ChangeRequestContent.create(
        payload.title,
        payload.description,
        payload.reason,
    )
    request = edit_change_request_content(
        uow, user, request_id, expected_version, content
    )
    return _response(request, response)


@router.post(
    "/{request_id}/submit",
    response_model=ChangeRequestResponse,
    operation_id="submitChangeRequest",
    responses=_responses(200, (401, 403, 404, 409, 428), etag=True),
)
def submit_request(
    request_id: UUID,
    response: Response,
    user: CurrentUserDependency,
    uow: UnitOfWorkDependency,
    expected_version: ExpectedVersionDependency,
) -> ChangeRequestResponse:
    request = submit_change_request(uow, user, request_id, expected_version)
    return _response(request, response)


@router.post(
    "/{request_id}/approve",
    response_model=ChangeRequestResponse,
    operation_id="approveChangeRequest",
    responses=_responses(200, (401, 403, 404, 409, 428), etag=True),
)
def approve_request(
    request_id: UUID,
    response: Response,
    user: CurrentUserDependency,
    uow: UnitOfWorkDependency,
    expected_version: ExpectedVersionDependency,
) -> ChangeRequestResponse:
    request = approve_change_request(uow, user, request_id, expected_version)
    return _response(request, response)


@router.post(
    "/{request_id}/request-changes",
    response_model=ChangeRequestResponse,
    operation_id="requestChangeRequestChanges",
    responses=_responses(200, (400, 401, 403, 404, 409, 428), etag=True),
)
def request_change_request(
    request_id: UUID,
    payload: RequestChangesRequest,
    response: Response,
    user: CurrentUserDependency,
    uow: UnitOfWorkDependency,
    expected_version: ExpectedVersionDependency,
) -> ChangeRequestResponse:
    request = request_changes(
        uow,
        user,
        request_id,
        expected_version,
        payload.comment,
    )
    return _response(request, response)


@router.get(
    "/{request_id}/history",
    response_model=ChangeRequestHistoryResponse,
    operation_id="getChangeRequestHistory",
    responses=_responses(200, (401, 403, 404), etag=False),
)
def get_history(
    request_id: UUID,
    user: CurrentUserDependency,
    uow: UnitOfWorkDependency,
) -> ChangeRequestHistoryResponse:
    transitions = get_change_request_history(uow, user, request_id)
    return ChangeRequestHistoryResponse(
        requestId=request_id,
        items=[
            ChangeRequestTransitionResponse.from_domain(transition)
            for transition in transitions
        ],
    )
