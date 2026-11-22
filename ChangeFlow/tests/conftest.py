import os
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

os.environ.setdefault("CHANGEFLOW_JWT_ISSUER", "https://issuer.test/")
os.environ.setdefault("CHANGEFLOW_JWT_AUDIENCE", "changeflow-api")
os.environ.setdefault("CHANGEFLOW_JWT_JWKS_URL", "https://issuer.test/jwks")

from changeflow.api.main import create_app  # noqa: E402
from changeflow.infrastructure.config import Settings  # noqa: E402
from changeflow.infrastructure.persistence.database import (  # noqa: E402
    create_database_engine,
    create_session_factory,
)
from changeflow.infrastructure.persistence.mappings import Base  # noqa: E402


class StubJwtVerifier:
    def __init__(self, tokens: dict[str, str] | None = None) -> None:
        self.tokens = tokens or {}

    def verify(self, token: str) -> str:
        from changeflow.application.errors import AuthenticationError

        if token not in self.tokens:
            raise AuthenticationError("caller credentials are invalid")
        return self.tokens[token]


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        environment="test",
        database_url=f"sqlite:///{tmp_path / 'changeflow-test.db'}",
        jwt_issuer="https://issuer.test/",
        jwt_audience="changeflow-api",
        jwt_jwks_url="https://issuer.test/jwks",
    )


@pytest.fixture
def engine(settings: Settings) -> Iterator[Engine]:
    database_engine = create_database_engine(settings)
    Base.metadata.create_all(database_engine)
    try:
        yield database_engine
    finally:
        database_engine.dispose()


@pytest.fixture
def session_factory(engine: Engine) -> sessionmaker[Session]:
    return create_session_factory(engine)


@pytest.fixture
def app(settings: Settings, engine: Engine):
    return create_app(
        settings,
        engine=engine,
        jwt_verifier=StubJwtVerifier({"valid-token": "user-1"}),
    )


@pytest.fixture
def client(app) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def seed_user(session_factory: sessionmaker[Session]) -> Callable[..., None]:
    from datetime import UTC, datetime

    from changeflow.domain.change_requests.enums import Role
    from changeflow.infrastructure.persistence.mappings import (
        UserAccountModel,
        UserRoleAssignmentModel,
    )

    def seed(
        user_id: str,
        roles: set[Role] | frozenset[Role],
        *,
        active: bool = True,
    ) -> None:
        now = datetime.now(UTC)
        with session_factory() as session:
            user = session.get(UserAccountModel, user_id)
            if user is None:
                user = UserAccountModel(
                    id=user_id,
                    is_active=active,
                    created_at=now,
                    updated_at=now,
                )
                session.add(user)
            else:
                user.is_active = active
                user.updated_at = now
            session.query(UserRoleAssignmentModel).filter_by(user_id=user_id).delete()
            for role in roles:
                session.add(UserRoleAssignmentModel(user_id=user_id, role=role.value))
            session.commit()

    return seed
