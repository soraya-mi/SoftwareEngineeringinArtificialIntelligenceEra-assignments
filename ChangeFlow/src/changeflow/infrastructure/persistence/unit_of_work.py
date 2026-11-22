from collections.abc import Callable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from changeflow.application.errors import ConcurrencyConflictError

from .mappings import ChangeRequestModel
from .repositories import SqlAlchemyChangeRequestRepository


class SqlAlchemyUnitOfWork:
    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory
        self._session: Session | None = None
        self._requests: SqlAlchemyChangeRequestRepository | None = None

    @property
    def session(self) -> Session:
        if self._session is None:
            self._session = self._session_factory()
        return self._session

    @property
    def requests(self) -> SqlAlchemyChangeRequestRepository:
        if self._requests is None:
            self._requests = SqlAlchemyChangeRequestRepository(self.session)
        return self._requests

    def commit(self, request_id: UUID | None = None) -> None:
        try:
            self.session.commit()
        except StaleDataError as exc:
            self.session.rollback()
            current_version = None
            if request_id is not None:
                current_version = self.session.scalar(
                    select(ChangeRequestModel.version).where(
                        ChangeRequestModel.id == request_id
                    )
                )
            raise ConcurrencyConflictError(
                "the request was changed by another operation",
                current_version=current_version,
            ) from exc

    def rollback(self) -> None:
        if self._session is not None:
            self._session.rollback()

    def close(self) -> None:
        if self._session is not None:
            self._session.close()
