from typing import Protocol
from uuid import UUID

from .change_request_repository import ChangeRequestRepository


class UnitOfWork(Protocol):
    @property
    def requests(self) -> ChangeRequestRepository: ...

    def commit(self, request_id: UUID | None = None) -> None: ...

    def rollback(self) -> None: ...
