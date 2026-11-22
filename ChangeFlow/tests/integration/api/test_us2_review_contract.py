from changeflow.domain.change_requests.enums import Role

from .auth_helpers import client_for_user, etag


def create_pending(app: object, owner: str) -> dict[str, object]:
    with client_for_user(app, owner, {Role.REQUESTER}) as client:
        created = client.post(
            "/api/change-requests",
            json={"title": "title", "description": "detail", "reason": "reason"},
        ).json()
        submitted = client.post(
            f"/api/change-requests/{created['id']}/submit",
            headers={"If-Match": etag(created)},
        )
        assert submitted.status_code == 200
        return submitted.json()


def test_reviewer_approves_another_users_request(app: object) -> None:
    pending = create_pending(app, "requester-1")
    with client_for_user(app, "reviewer-1", {Role.REVIEWER}) as reviewer:
        listed = reviewer.get("/api/change-requests")
        assert [item["id"] for item in listed.json()["items"]] == [pending["id"]]
        approved = reviewer.post(
            f"/api/change-requests/{pending['id']}/approve",
            headers={"If-Match": etag(pending)},
        )
        assert approved.status_code == 200
        assert approved.json()["status"] == "Approved"


def test_self_approval_and_blank_comment_are_rejected(app: object) -> None:
    pending = create_pending(app, "requester-1")
    with client_for_user(
        app, "requester-1", {Role.REQUESTER, Role.REVIEWER}
    ) as dual_role:
        self_approval = dual_role.post(
            f"/api/change-requests/{pending['id']}/approve",
            headers={"If-Match": etag(pending)},
        )
        assert self_approval.status_code == 403
        assert self_approval.json()["code"] == "SELF_APPROVAL_FORBIDDEN"

        blank_comment = dual_role.post(
            f"/api/change-requests/{pending['id']}/request-changes",
            headers={"If-Match": etag(pending)},
            json={"comment": "   "},
        )
        assert blank_comment.status_code == 400


def test_owner_may_request_changes_on_own_request(app: object) -> None:
    pending = create_pending(app, "requester-1")
    with client_for_user(
        app, "requester-1", {Role.REQUESTER, Role.REVIEWER}
    ) as dual_role:
        response = dual_role.post(
            f"/api/change-requests/{pending['id']}/request-changes",
            headers={"If-Match": etag(pending)},
            json={"comment": "  retain this text  "},
        )
        assert response.status_code == 200
        history = dual_role.get(f"/api/change-requests/{pending['id']}/history").json()
        assert history["items"][-1]["comment"] == "  retain this text  "
