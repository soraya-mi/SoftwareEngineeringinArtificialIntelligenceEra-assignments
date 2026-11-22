from fastapi.testclient import TestClient

from changeflow.domain.change_requests.enums import Role

from .auth_helpers import client_for_user


def test_validation_error_does_not_echo_secret_body(app: object) -> None:
    with client_for_user(app, "requester-1", {Role.REQUESTER}) as client:
        response = client.post(
            "/api/change-requests",
            json={
                "title": "SECRET-TITLE",
                "description": "",
                "reason": "SECRET-REASON",
            },
        )
        assert response.status_code == 400
        assert "SECRET-TITLE" not in response.text
        assert "SECRET-REASON" not in response.text


def test_authentication_error_does_not_echo_token(client: TestClient) -> None:
    response = client.get(
        "/api/change-requests",
        headers={"Authorization": "Bearer SECRET-TOKEN"},
    )
    assert response.status_code == 401
    assert "SECRET-TOKEN" not in response.text
