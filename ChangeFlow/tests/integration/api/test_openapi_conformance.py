import json
from pathlib import Path

from changeflow.api.main import app

CONTRACT = json.loads(
    Path("specs/001-change-request-workflow/contracts/openapi.json").read_text(
        encoding="utf-8"
    )
)


def test_generated_operations_match_contract_operation_ids() -> None:
    generated = app.openapi()
    operation_ids = {
        operation.get("operationId")
        for path in generated["paths"].values()
        for operation in path.values()
        if isinstance(operation, dict)
    }
    assert {
        "listVisibleChangeRequests",
        "createChangeRequest",
        "getChangeRequest",
        "deleteChangeRequest",
        "updateChangeRequestContent",
        "submitChangeRequest",
        "approveChangeRequest",
        "requestChangeRequestChanges",
        "getChangeRequestHistory",
    } <= operation_ids


def test_generated_contract_includes_etag_problem_details_and_if_match() -> None:
    generated = app.openapi()
    mutations = {
        "/api/change-requests/{request_id}/content": "put",
        "/api/change-requests/{request_id}/submit": "post",
        "/api/change-requests/{request_id}/approve": "post",
        "/api/change-requests/{request_id}/request-changes": "post",
    }
    for path, method in mutations.items():
        operation = generated["paths"][path][method]
        parameters = {
            parameter["name"] for parameter in operation.get("parameters", [])
        }
        assert "If-Match" in parameters
        assert "ETag" in operation["responses"]["200"].get("headers", {})
        conflict = operation["responses"]["409"]
        assert "application/problem+json" in conflict["content"]

    generated_codes = set(
        generated["components"]["schemas"]["ErrorCode"].get("enum", [])
    )
    contract_codes = set(
        CONTRACT["components"]["schemas"]["ErrorCode"].get("enum", [])
    )
    assert generated_codes == contract_codes
