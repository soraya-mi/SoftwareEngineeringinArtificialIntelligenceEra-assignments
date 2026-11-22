class DomainError(Exception):
    """Base class for rule violations owned by the domain."""


class DomainValidationError(DomainError):
    """Submitted domain values are structurally invalid."""


class InvalidWorkflowError(DomainError):
    """The current state or actor relationship does not permit the action."""


class SelfApprovalForbiddenError(DomainError):
    """A request owner attempted to approve their own request."""
