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
