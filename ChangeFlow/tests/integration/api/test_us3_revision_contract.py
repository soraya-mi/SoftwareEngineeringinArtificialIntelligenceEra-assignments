from changeflow.domain.change_requests.enums import Role

from .auth_helpers import client_for_user, etag


def changes_requested(app: object) -> tuple[dict[str, object], dict[str, object]]:
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
        revised = reviewer.post(
            f"/api/change-requests/{pending['id']}/request-changes",
            headers={"If-Match": etag(pending)},
            json={"comment": "Please revise"},
        ).json()
    return created, revised


def test_unchanged_resubmission_is_rejected_and_changed_resubmission_succeeds(
    app: object,
) -> None:
    _, revised = changes_requested(app)
    with client_for_user(app, "requester-1", {Role.REQUESTER}) as requester:
        request_id = revised["id"]
        unchanged = requester.post(
            f"/api/change-requests/{request_id}/submit",
            headers={"If-Match": etag(revised)},
        )
        assert unchanged.status_code == 409
        assert unchanged.json()["code"] == "INVALID_WORKFLOW"

        edited = requester.put(
            f"/api/change-requests/{request_id}/content",
            headers={"If-Match": etag(revised)},
            json={"title": "revised", "description": "detail", "reason": "reason"},
        )
        assert edited.status_code == 200
        resubmitted = requester.post(
            f"/api/change-requests/{request_id}/submit",
            headers={"If-Match": etag(edited.json())},
        )
        assert resubmitted.status_code == 200
        assert resubmitted.json()["status"] == "PendingReview"

        history = requester.get(f"/api/change-requests/{request_id}/history").json()
        assert [item["action"] for item in history["items"]] == [
            "Submit",
            "RequestChanges",
            "Submit",
        ]


def test_approved_request_is_immutable(app: object) -> None:
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
        denied = requester.put(
            f"/api/change-requests/{approved['id']}/content",
            headers={"If-Match": etag(approved)},
            json={"title": "new", "description": "detail", "reason": "reason"},
        )
        assert denied.status_code == 409
