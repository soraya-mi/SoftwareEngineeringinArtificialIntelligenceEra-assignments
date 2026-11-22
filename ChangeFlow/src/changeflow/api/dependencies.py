import re
from collections.abc import Generator
from typing import Annotated, cast
from uuid import UUID

from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from changeflow.application.errors import (
    AuthenticationError,
    PreconditionRequiredError,
)
from changeflow.application.ports.current_user_role_store import CurrentUser
from changeflow.infrastructure.auth.current_user_role_store import (
    SqlAlchemyCurrentUserRoleStore,
)
from changeflow.infrastructure.persistence.database import SessionFactory
from changeflow.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork

_ETAG_PATTERN = re.compile(r'^"([0-9a-fA-F-]{36})"$')
_bearer = HTTPBearer(auto_error=False)


def get_session_factory(request: Request) -> SessionFactory:
    return cast(SessionFactory, request.app.state.session_factory)


def get_current_user(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_bearer)
    ],
) -> CurrentUser:
    if credentials is None:
        raise AuthenticationError("authentication is required")
    user_id = request.app.state.jwt_verifier.verify(credentials.credentials)
    store = SqlAlchemyCurrentUserRoleStore(get_session_factory(request))
    user = store.get(user_id)
    if user is None:
        raise AuthenticationError("caller credentials are invalid")
    return user


def get_unit_of_work(request: Request) -> Generator[SqlAlchemyUnitOfWork, None, None]:
    uow = SqlAlchemyUnitOfWork(get_session_factory(request))
    try:
        yield uow
    except Exception:
        uow.rollback()
        raise
    finally:
        uow.close()


def get_expected_version(
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
) -> UUID:
    if if_match is None:
        raise PreconditionRequiredError("If-Match is required")
    match = _ETAG_PATTERN.match(if_match)
    if not match:
        raise PreconditionRequiredError("If-Match must be a quoted UUID ETag")
    return UUID(match.group(1))


def quote_etag(version: UUID) -> str:
    return f'"{version}"'


CurrentUserDependency = Annotated[CurrentUser, Depends(get_current_user)]
UnitOfWorkDependency = Annotated[SqlAlchemyUnitOfWork, Depends(get_unit_of_work)]
ExpectedVersionDependency = Annotated[UUID, Depends(get_expected_version)]
