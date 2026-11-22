import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from changeflow.application.errors import (
    ApplicationError,
    AuthenticationError,
    ConcurrencyConflictError,
)
from changeflow.domain.change_requests.errors import (
    DomainValidationError,
    InvalidWorkflowError,
    SelfApprovalForbiddenError,
)

logger = logging.getLogger(__name__)


def _problem(
    request: Request,
    *,
    status: int,
    title: str,
    code: str,
    detail: str | None = None,
    current_version: object | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    content: dict[str, object] = {
        "type": "about:blank",
        "title": title,
        "status": status,
        "detail": detail,
        "instance": request.url.path,
        "code": code,
    }
    if current_version is not None:
        content["currentVersion"] = str(current_version)
    return JSONResponse(
        status_code=status,
        content=content,
        media_type="application/problem+json",
        headers=headers,
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_error(
        request: Request, _: RequestValidationError
    ) -> JSONResponse:
        return _problem(
            request,
            status=400,
            title="Validation failed",
            code="VALIDATION_FAILED",
            detail="request content is invalid",
        )

    @app.exception_handler(DomainValidationError)
    async def domain_validation_error(
        request: Request, exc: DomainValidationError
    ) -> JSONResponse:
        return _problem(
            request,
            status=400,
            title="Validation failed",
            code="VALIDATION_FAILED",
            detail=str(exc),
        )

    @app.exception_handler(InvalidWorkflowError)
    async def domain_workflow_error(
        request: Request, exc: InvalidWorkflowError
    ) -> JSONResponse:
        return _problem(
            request,
            status=409,
            title="Invalid workflow action",
            code="INVALID_WORKFLOW",
            detail=str(exc),
        )

    @app.exception_handler(SelfApprovalForbiddenError)
    async def self_approval_error(
        request: Request, exc: SelfApprovalForbiddenError
    ) -> JSONResponse:
        return _problem(
            request,
            status=403,
            title="Self-approval forbidden",
            code="SELF_APPROVAL_FORBIDDEN",
            detail=str(exc),
        )

    @app.exception_handler(ConcurrencyConflictError)
    async def concurrency_error(
        request: Request, exc: ConcurrencyConflictError
    ) -> JSONResponse:
        return _problem(
            request,
            status=409,
            title="Concurrency conflict",
            code="CONCURRENCY_CONFLICT",
            detail=exc.detail,
            current_version=exc.current_version,
        )

    @app.exception_handler(AuthenticationError)
    async def authentication_error(
        request: Request, exc: AuthenticationError
    ) -> JSONResponse:
        return _problem(
            request,
            status=401,
            title="Authentication required",
            code="AUTHENTICATION_REQUIRED",
            detail=exc.detail,
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(ApplicationError)
    async def application_error(request: Request, exc: ApplicationError) -> JSONResponse:
        return _problem(
            request,
            status=exc.status_code,
            title=exc.code.replace("_", " ").title(),
            code=exc.code,
            detail=exc.detail,
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        if exc.status_code == 405:
            code = "DELETION_NOT_SUPPORTED"
            title = "Deletion not supported"
            detail = "change request deletion is not supported"
        elif exc.status_code == 404:
            code = "RESOURCE_NOT_FOUND"
            title = "Not found"
            detail = "resource was not found"
        else:
            code = "HTTP_ERROR"
            title = "HTTP error"
            detail = "request could not be completed"
        return _problem(
            request,
            status=exc.status_code,
            title=title,
            code=code,
            detail=detail,
            headers=dict(exc.headers) if exc.headers is not None else None,
        )

    @app.exception_handler(Exception)
    async def unhandled_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled API error", exc_info=exc)
        return _problem(
            request,
            status=500,
            title="Internal server error",
            code="INTERNAL_SERVER_ERROR",
            detail="the request could not be completed",
        )
