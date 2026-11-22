from changeflow.domain.change_requests.enums import Role

from .auth_helpers import client_for_user, etag


def test_stale_etag_returns_distinct_concurrency_conflict(app: object) -> None:
    with client_for_user(app, "requester-1", {Role.REQUESTER}) as client:
        created = client.post(
            "/api/change-requests",
            json={"title": "title", "description": "detail", "reason": "reason"},
        ).json()
        first = client.put(
            f"/api/change-requests/{created['id']}/content",
            headers={"If-Match": etag(created)},
            json={"title": "first", "description": "detail", "reason": "reason"},
        )
        assert first.status_code == 200
        stale = client.put(
            f"/api/change-requests/{created['id']}/content",
            headers={"If-Match": etag(created)},
            json={"title": "stale", "description": "detail", "reason": "reason"},
        )
        assert stale.status_code == 409
        assert stale.json()["code"] == "CONCURRENCY_CONFLICT"
        assert stale.json()["currentVersion"] == first.json()["version"]


def test_missing_if_match_returns_precondition_required(app: object) -> None:
    with client_for_user(app, "requester-1", {Role.REQUESTER}) as client:
        created = client.post(
            "/api/change-requests",
            json={"title": "title", "description": "detail", "reason": "reason"},
        ).json()
        response = client.put(
            f"/api/change-requests/{created['id']}/content",
            json={"title": "new", "description": "detail", "reason": "reason"},
        )
        assert response.status_code == 428
