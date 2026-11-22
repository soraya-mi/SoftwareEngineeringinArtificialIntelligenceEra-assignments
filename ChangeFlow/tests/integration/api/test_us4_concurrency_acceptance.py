from changeflow.domain.change_requests.enums import Role

from .auth_helpers import client_for_user, etag


def test_two_clients_using_same_etag_produce_one_winner(app: object) -> None:
    with client_for_user(app, "requester-1", {Role.REQUESTER}) as first_client:
        created = first_client.post(
            "/api/change-requests",
            json={"title": "title", "description": "detail", "reason": "reason"},
        ).json()
        first = first_client.put(
            f"/api/change-requests/{created['id']}/content",
            headers={"If-Match": etag(created)},
            json={"title": "first", "description": "detail", "reason": "reason"},
        )
        with client_for_user(app, "requester-1", {Role.REQUESTER}) as second_client:
            second = second_client.put(
                f"/api/change-requests/{created['id']}/content",
                headers={"If-Match": etag(created)},
                json={"title": "second", "description": "detail", "reason": "reason"},
            )
        persisted = first_client.get(
            f"/api/change-requests/{created['id']}"
        ).json()
        assert first.status_code == 200
        assert second.status_code == 409
        assert persisted["title"] == "first"
