from fastapi import FastAPI
from sqlalchemy.engine import Engine

from changeflow.api.error_handlers import register_exception_handlers
from changeflow.api.routes import router
from changeflow.infrastructure.auth.jwt_verifier import JwtVerifier
from changeflow.infrastructure.config import Settings, get_settings
from changeflow.infrastructure.persistence.database import (
    create_database_engine,
    create_session_factory,
)


def create_app(
    settings: Settings | None = None,
    *,
    jwt_verifier: JwtVerifier | None = None,
    engine: Engine | None = None,
) -> FastAPI:
    active_settings = settings or get_settings()
    active_engine = engine or create_database_engine(active_settings)

    app = FastAPI(title="ChangeFlow Change Request API", version="1.0.0")
    app.state.settings = active_settings
    app.state.engine = active_engine
    app.state.session_factory = create_session_factory(active_engine)
    app.state.jwt_verifier = jwt_verifier or JwtVerifier(active_settings)
    register_exception_handlers(app)
    app.include_router(router)
    return app


app = create_app()
