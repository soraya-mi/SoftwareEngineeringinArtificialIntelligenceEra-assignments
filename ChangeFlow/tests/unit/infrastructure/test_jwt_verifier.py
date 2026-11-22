from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from changeflow.application.errors import AuthenticationError
from changeflow.infrastructure.auth.jwt_verifier import JwtVerifier
from changeflow.infrastructure.config import Settings


def make_verifier(private_key: object, public_key: object) -> tuple[JwtVerifier, callable]:
    settings = Settings(
        jwt_issuer="https://issuer.test/",
        jwt_audience="changeflow-api",
        jwt_jwks_url="https://issuer.test/jwks",
    )
    resolver = SimpleNamespace(
        get_signing_key_from_jwt=lambda token: SimpleNamespace(key=public_key)
    )
    verifier = JwtVerifier(settings, signing_key_resolver=resolver)  # type: ignore[arg-type]

    def encode(**overrides: object) -> str:
        now = datetime.now(UTC)
        claims: dict[str, object] = {
            "sub": "user-1",
            "iss": "https://issuer.test/",
            "aud": "changeflow-api",
            "iat": now,
            "exp": now + timedelta(minutes=5),
        }
        claims.update(overrides)
        return jwt.encode(claims, private_key, algorithm="RS256")  # type: ignore[arg-type]

    return verifier, encode


def test_valid_token_returns_subject() -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    verifier, encode = make_verifier(private_key, private_key.public_key())
    assert verifier.verify(encode()) == "user-1"


@pytest.mark.parametrize(
    "override",
    [
        {"iss": "https://wrong.test/"},
        {"aud": "wrong-api"},
        {"exp": datetime.now(UTC) - timedelta(minutes=1)},
        {"sub": None},
    ],
)
def test_invalid_claims_are_rejected(override: dict[str, object]) -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    verifier, encode = make_verifier(private_key, private_key.public_key())
    with pytest.raises(AuthenticationError):
        verifier.verify(encode(**override))


def test_bad_signature_is_rejected() -> None:
    trusted = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    attacker = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    verifier, encode = make_verifier(trusted, trusted.public_key())
    bad_token = jwt.encode(
        {
            "sub": "user-1",
            "iss": "https://issuer.test/",
            "aud": "changeflow-api",
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        },
        attacker,
        algorithm="RS256",
    )
    with pytest.raises(AuthenticationError):
        verifier.verify(bad_token)
