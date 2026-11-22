from dataclasses import dataclass

from .errors import DomainValidationError


def normalize_required(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise DomainValidationError(f"{field_name} must not be empty")
    return normalized


@dataclass(frozen=True)
class ChangeRequestContent:
    title: str
    description: str
    reason: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "title", normalize_required(self.title, "title"))
        object.__setattr__(
            self,
            "description",
            normalize_required(self.description, "description"),
        )
        object.__setattr__(self, "reason", normalize_required(self.reason, "reason"))

    @classmethod
    def create(cls, title: str, description: str, reason: str) -> "ChangeRequestContent":
        return cls(title=title, description=description, reason=reason)


def validate_review_comment(comment: str) -> str:
    if not comment.strip():
        raise DomainValidationError("comment must not be empty")
    return comment
