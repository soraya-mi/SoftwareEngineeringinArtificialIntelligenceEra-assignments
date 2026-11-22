from fastapi.testclient import TestClient

from changeflow.domain.change_requests.enums import Role

from .auth_helpers import client_for_user, etag


def pending_for(app: object, owner: str) -> dict[str, object]:
    with client_for_user(app, owner, {Role.REQUESTER}) as requester:
        created = requester.post(
            "/api/change-requests",
            json={"title": "title", "description": "detail", "reason": "reason"},
        ).json()
        return requester.post(
            f"/api/change-requests/{created['id']}/submit",
            headers={"If-Match": etag(created)},
        ).json()


def test_reviewer_role_revocation_is_effective_on_next_request(
    app: object,
    seed_user,
) -> None:
    pending = pending_for(app, "requester-1")
    seed_user("user-1", {Role.REVIEWER})
    with TestClient(app) as client:
        headers = {"Authorization": "Bearer valid-token"}
        assert client.get("/api/change-requests", headers=headers).status_code == 200

        seed_user("user-1", {Role.REQUESTER})
        denied = client.post(
            f"/api/change-requests/{pending['id']}/approve",
            headers={**headers, "If-Match": etag(pending)},
        )
        assert denied.status_code == 403
