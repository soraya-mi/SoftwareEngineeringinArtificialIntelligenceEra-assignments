from typing import Protocol
from uuid import UUID

from changeflow.domain.change_requests.entities import (
    ChangeRequest,
    ChangeRequestRevision,
    ChangeRequestTransition,
)


class ChangeRequestRepository(Protocol):
    def get(self, request_id: UUID) -> ChangeRequest | None: ...

    def list_all(self) -> list[ChangeRequest]: ...

    def save(self, request: ChangeRequest) -> ChangeRequest: ...

    def get_revision(self, revision_id: UUID) -> ChangeRequestRevision | None: ...

    def get_latest_submitted_revision(
        self, request_id: UUID
    ) -> ChangeRequestRevision | None: ...

    def next_revision_number(self, request_id: UUID) -> int: ...

    def add_revision(self, revision: ChangeRequestRevision) -> None: ...

    def add_transition(self, transition: ChangeRequestTransition) -> None: ...

    def list_transitions(self, request_id: UUID) -> list[ChangeRequestTransition]: ...
