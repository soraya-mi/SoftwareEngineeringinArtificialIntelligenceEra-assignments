from changeflow.domain.change_requests.enums import Role

from .auth_helpers import client_for_user, etag


def test_approved_request_rejects_edit_and_submit_without_state_change(
    app: object,
) -> None:
    with client_for_user(app, "requester-1", {Role.REQUESTER}) as requester:
        created = requester.post(
            "/api/change-requests",
            json={"title": "title", "description": "detail", "reason": "reason"},
        ).json()
        pending = requester.post(
            f"/api/change-requests/{created['id']}/submit",
            headers={"If-Match": etag(created)},
        ).json()
    with client_for_user(app, "reviewer-1", {Role.REVIEWER}) as reviewer:
        approved = reviewer.post(
            f"/api/change-requests/{pending['id']}/approve",
            headers={"If-Match": etag(pending)},
        ).json()
    with client_for_user(app, "requester-1", {Role.REQUESTER}) as requester:
        edit = requester.put(
            f"/api/change-requests/{approved['id']}/content",
            headers={"If-Match": etag(approved)},
            json={"title": "changed", "description": "detail", "reason": "reason"},
        )
        submit = requester.post(
            f"/api/change-requests/{approved['id']}/submit",
            headers={"If-Match": etag(approved)},
        )
        detail = requester.get(f"/api/change-requests/{approved['id']}").json()
        history = requester.get(
            f"/api/change-requests/{approved['id']}/history"
        ).json()
        assert edit.status_code == 409
        assert submit.status_code == 409
        assert detail["status"] == "Approved"
        assert detail["version"] == approved["version"]
        assert detail["title"] == approved["title"]
        assert [item["action"] for item in history["items"]] == ["Submit", "Approve"]
