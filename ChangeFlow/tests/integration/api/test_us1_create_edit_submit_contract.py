
from changeflow.domain.change_requests.enums import Role

from .auth_helpers import client_for_user, etag


def payload(title: str = "title") -> dict[str, str]:
    return {"title": title, "description": "detail", "reason": "reason"}


def test_create_edit_list_detail_history_and_submit(app: object) -> None:
    with client_for_user(app, "requester-1", {Role.REQUESTER}) as client:
        created = client.post("/api/change-requests", json=payload())
        assert created.status_code == 201
        body = created.json()
        assert body["status"] == "Draft"
        assert body["requesterId"] == "requester-1"
        assert created.headers["ETag"] == etag(body)
        request_id = body["id"]

        listed = client.get("/api/change-requests")
        assert listed.status_code == 200
        assert [item["id"] for item in listed.json()["items"]] == [request_id]

        detail = client.get(f"/api/change-requests/{request_id}")
        assert detail.status_code == 200

        updated = client.put(
            f"/api/change-requests/{request_id}/content",
            headers={"If-Match": etag(body)},
            json=payload("updated"),
        )
        assert updated.status_code == 200
        updated_body = updated.json()
        assert updated_body["title"] == "updated"

        submitted = client.post(
            f"/api/change-requests/{request_id}/submit",
            headers={"If-Match": etag(updated_body)},
        )
        assert submitted.status_code == 200
        assert submitted.json()["status"] == "PendingReview"

        history = client.get(f"/api/change-requests/{request_id}/history")
        assert history.status_code == 200
        assert history.json()["items"][0]["action"] == "Submit"


def test_validation_if_match_and_duplicate_submit(app: object) -> None:
    with client_for_user(app, "requester-1", {Role.REQUESTER}) as client:
        invalid = client.post(
            "/api/change-requests",
            json={"title": "  ", "description": "d", "reason": "r"},
        )
        assert invalid.status_code == 400
        assert invalid.json()["code"] == "VALIDATION_FAILED"

        created = client.post("/api/change-requests", json=payload()).json()
        request_id = created["id"]
        missing = client.post(f"/api/change-requests/{request_id}/submit")
        assert missing.status_code == 428

        submitted = client.post(
            f"/api/change-requests/{request_id}/submit",
            headers={"If-Match": etag(created)},
        ).json()
        repeated = client.post(
            f"/api/change-requests/{request_id}/submit",
            headers={"If-Match": etag(submitted)},
        )
        assert repeated.status_code == 409
        assert repeated.json()["code"] == "INVALID_WORKFLOW"
