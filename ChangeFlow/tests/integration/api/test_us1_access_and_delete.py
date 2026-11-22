from fastapi.testclient import TestClient

from changeflow.domain.change_requests.enums import Role

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
