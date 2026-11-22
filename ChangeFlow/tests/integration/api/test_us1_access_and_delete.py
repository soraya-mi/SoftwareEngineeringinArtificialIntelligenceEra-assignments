from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from changeflow.api.main import create_app
from changeflow.domain.change_requests.enums import Role
from changeflow.infrastructure.auth.jwt_verifier import JwtVerifier
from changeflow.infrastructure.config import Settings

from .auth_helpers import client_for_user


def test_authentication_is_required(client: TestClient) -> None:
    response = client.get("/api/change-requests")
    assert response.status_code == 401
    assert response.json()["code"] == "AUTHENTICATION_REQUIRED"


def test_invalid_token_is_rejected(client: TestClient) -> None:
    response = client.get(
        "/api/change-requests",
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert response.status_code == 401


def test_non_owner_cannot_modify_and_delete_is_rejected(app: object) -> None:
    with client_for_user(app, "requester-1", {Role.REQUESTER}) as owner:
        created = owner.post(
            "/api/change-requests",
            json={"title": "title", "description": "detail", "reason": "reason"},
        ).json()
    with client_for_user(app, "requester-2", {Role.REQUESTER}) as other:
        request_id = created["id"]
        denied = other.get(f"/api/change-requests/{request_id}")
        assert denied.status_code == 403
        denied_history = other.get(f"/api/change-requests/{request_id}/history")
        assert denied_history.status_code == 403
        deleted = other.delete(f"/api/change-requests/{request_id}")
        assert deleted.status_code == 405
        assert deleted.json()["code"] == "DELETION_NOT_SUPPORTED"


def test_client_cannot_spoof_requester_or_status(app: object) -> None:
    with client_for_user(app, "requester-1", {Role.REQUESTER}) as client:
        response = client.post(
            "/api/change-requests",
            json={
                "title": "title",
                "description": "detail",
                "reason": "reason",
                "requesterId": "someone-else",
                "status": "Approved",
            },
        )
        assert response.status_code == 400


def test_api_rejects_expired_wrong_audience_unknown_and_inactive_users(
    settings: Settings,
    engine,
    seed_user,
) -> None:
    seed_user("known-user", {Role.REQUESTER})
    seed_user("inactive-user", {Role.REQUESTER}, active=False)
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    resolver = SimpleNamespace(
        get_signing_key_from_jwt=lambda token: SimpleNamespace(
            key=private_key.public_key()
        )
    )
    verifier = JwtVerifier(settings, signing_key_resolver=resolver)  # type: ignore[arg-type]
    real_app = create_app(settings, engine=engine, jwt_verifier=verifier)

    def token(**overrides: object) -> str:
        now = datetime.now(UTC)
        claims: dict[str, object] = {
            "sub": "known-user",
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "iat": now,
            "exp": now + timedelta(minutes=5),
        }
        claims.update(overrides)
        return jwt.encode(claims, private_key, algorithm="RS256")

    cases = [
        token(exp=datetime.now(UTC) - timedelta(minutes=1)),
        token(aud="wrong-api"),
        token(iss="https://wrong.test/"),
        token(sub="unknown-user"),
        token(sub="inactive-user"),
    ]
    with TestClient(real_app) as client:
        for credentials in cases:
            response = client.get(
                "/api/change-requests",
                headers={"Authorization": f"Bearer {credentials}"},
            )
            assert response.status_code == 401
            assert response.json()["code"] == "AUTHENTICATION_REQUIRED"
