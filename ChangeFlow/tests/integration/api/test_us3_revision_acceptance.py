from changeflow.domain.change_requests.enums import Role

from .auth_helpers import client_for_user, etag


def test_revision_loop_exposes_prior_feedback(app: object) -> None:
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
        changed = reviewer.post(
            f"/api/change-requests/{pending['id']}/request-changes",
            headers={"If-Match": etag(pending)},
            json={"comment": "Add impact"},
        ).json()
    with client_for_user(app, "requester-1", {Role.REQUESTER}) as requester:
        edited = requester.put(
            f"/api/change-requests/{changed['id']}/content",
            headers={"If-Match": etag(changed)},
            json={"title": "title", "description": "new impact", "reason": "reason"},
        ).json()
        resubmitted = requester.post(
            f"/api/change-requests/{changed['id']}/submit",
            headers={"If-Match": etag(edited)},
        )
        history = requester.get(
            f"/api/change-requests/{changed['id']}/history"
        ).json()
        assert resubmitted.status_code == 200
        assert [item["action"] for item in history["items"]] == [
            "Submit",
            "RequestChanges",
            "Submit",
        ]
        assert history["items"][1]["comment"] == "Add impact"
