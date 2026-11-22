from uuid import UUID


class ApplicationError(Exception):
    status_code = 400
    code = "APPLICATION_ERROR"

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class AuthenticationError(ApplicationError):
    status_code = 401
    code = "AUTHENTICATION_REQUIRED"


class AuthorizationDeniedError(ApplicationError):
    status_code = 403
    code = "AUTHORIZATION_DENIED"


class SelfApprovalForbiddenError(AuthorizationDeniedError):
    code = "SELF_APPROVAL_FORBIDDEN"


class NotFoundError(ApplicationError):
    status_code = 404
    code = "RESOURCE_NOT_FOUND"


class ValidationFailedError(ApplicationError):
    status_code = 400
    code = "VALIDATION_FAILED"


class InvalidWorkflowError(ApplicationError):
    status_code = 409
    code = "INVALID_WORKFLOW"


class ConcurrencyConflictError(ApplicationError):
    status_code = 409
    code = "CONCURRENCY_CONFLICT"

    def __init__(self, detail: str, current_version: UUID | None = None) -> None:
        super().__init__(detail)
        self.current_version = current_version


class PreconditionRequiredError(ApplicationError):
    status_code = 428
    code = "PRECONDITION_REQUIRED"


class DeletionNotSupportedError(ApplicationError):
    status_code = 405
    code = "DELETION_NOT_SUPPORTED"
