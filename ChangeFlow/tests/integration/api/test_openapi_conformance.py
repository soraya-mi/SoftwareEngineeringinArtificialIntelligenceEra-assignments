from changeflow.api.main import app


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
