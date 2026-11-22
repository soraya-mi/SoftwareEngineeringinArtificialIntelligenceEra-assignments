import pytest
from pydantic import ValidationError

from changeflow.infrastructure.config import Settings


def test_settings_load_required_values() -> None:
    settings = Settings(
        jwt_issuer="https://issuer.test/",
        jwt_audience="changeflow-api",
        jwt_jwks_url="https://issuer.test/jwks",
    )
    assert settings.jwt_audience == "changeflow-api"


def test_settings_reject_missing_jwt_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CHANGEFLOW_JWT_ISSUER", raising=False)
    monkeypatch.delenv("CHANGEFLOW_JWT_AUDIENCE", raising=False)
    monkeypatch.delenv("CHANGEFLOW_JWT_JWKS_URL", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)
