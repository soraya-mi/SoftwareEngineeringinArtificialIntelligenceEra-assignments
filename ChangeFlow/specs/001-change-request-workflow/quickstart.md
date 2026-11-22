# Phase 1 Quickstart and Validation Guide

**Feature**: `001-change-request-workflow`

This guide defines how to run and validate the planned Python implementation. It does
not contain application code or replace the API contract at
[contracts/openapi.json](contracts/openapi.json).

## Prerequisites

- Python 3.12.x, already installed in the current environment.
- A virtual environment with FastAPI, SQLAlchemy, Alembic, PyJWT, Uvicorn, pytest,
  HTTPX, Ruff, and mypy installed from the committed lock files.
- A valid JWT access token from the configured identity provider.
- A SQLite-capable local filesystem.

Verify Python:

```powershell
python --version
python -m pip --version
```

The reported version must be Python 3.12.x.

## Environment Setup

Use environment variables for local configuration so secrets are not committed:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.lock
.\.venv\Scripts\python.exe -m pip install -e . --no-deps
```

Configure the API:

```powershell
$env:CHANGEFLOW_ENVIRONMENT = "development"
$env:CHANGEFLOW_DATABASE_URL = "sqlite:///changeflow.dev.db"
$env:CHANGEFLOW_JWT_ISSUER = "https://identity.example/"
$env:CHANGEFLOW_JWT_AUDIENCE = "changeflow-api"
$env:CHANGEFLOW_JWT_JWKS_URL = "https://identity.example/.well-known/jwks.json"
```

The identity provider must issue access tokens whose `sub` claim maps to a
pre-provisioned ChangeFlow user. User and role-administration routes are outside this
feature; tests seed current role assignments through persistence fixtures.

## Migrate, Lint, and Test

Run from the `ChangeFlow` repository root:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\ruff check src tests
.\.venv\Scripts\mypy src
.\.venv\Scripts\python.exe -m pytest
```

Expected outcome:

- All migrations apply successfully to a new SQLite database.
- Ruff reports no lint violations.
- mypy reports no type errors.
- All unit, integration, persistence, concurrency, architecture, and contract tests
  pass.

Useful focused checks:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/domain -m workflow
.\.venv\Scripts\python.exe -m pytest tests/unit/application -m authorization
.\.venv\Scripts\python.exe -m pytest tests/integration/concurrency
.\.venv\Scripts\python.exe -m pytest tests/integration/api -m contract
.\.venv\Scripts\python.exe -m pytest tests/architecture
```

## Run the API

```powershell
.\.venv\Scripts\python.exe -m uvicorn changeflow.api.main:app --port 5001 --reload
```

The development API exposes:

- API base: `http://localhost:5001`
- Interactive documentation: `http://localhost:5001/docs`
- Generated OpenAPI: `http://localhost:5001/openapi.json`

For manual checks:

```powershell
$env:CHANGEFLOW_TOKEN = "<access-token>"
$headers = @{ Authorization = "Bearer $env:CHANGEFLOW_TOKEN" }
Invoke-RestMethod -Method Get `
  -Uri "http://localhost:5001/api/change-requests" `
  -Headers $headers
```

Do not print the token or commit it to configuration files.

## End-to-End Validation Scenarios

Run these scenarios against the implementation or its test client. Each scenario must
also be represented by automated tests.

### Authentication and Visibility

1. Call any endpoint without a token.
   - Expect `401 AUTHENTICATION_REQUIRED`.
2. Authenticate a Requester and create a request.
   - Expect `201`, `Draft`, requester equal to the token subject, and an `ETag`.
3. Try to read another user's request as a Requester.
   - Expect `403 AUTHORIZATION_DENIED` and no content exposure.
4. Authenticate a Reviewer and list requests.
   - Expect other users' `PendingReview` requests and requests they reviewed, but no
     unrelated Draft or Approved requests.
5. Request history or review feedback without request visibility.
   - Expect `403 AUTHORIZATION_DENIED`.

### Create, Edit, and Submit

1. Create with a blank or whitespace-only title, description, or reason.
   - Expect `400 VALIDATION_FAILED`; verify no request or edit was persisted.
2. Edit an owned Draft with the current ETag in `If-Match`.
   - Expect `200`, updated normalized content, `Draft`, and a new ETag.
3. Repeat the edit with the previous ETag.
   - Expect `409 CONCURRENCY_CONFLICT`; verify the newer content was not overwritten.
4. Submit an owned Draft with the current ETag.
   - Expect `200` and `PendingReview`; verify a content revision and Submit transition
     were persisted.
5. Submit the same request again with its current ETag.
   - Expect `409 INVALID_WORKFLOW`; verify no duplicate transition.
6. Submit without `If-Match`.
   - Expect `428 PRECONDITION_REQUIRED`.

### Review Decisions

1. As a Reviewer, approve another user's `PendingReview` request.
   - Expect `200` and `Approved`.
2. As a dual-role owner, attempt to approve their own request.
   - Expect `403 SELF_APPROVAL_FORBIDDEN`; verify status, version, and history are
     unchanged.
3. As a dual-role owner, request changes on their own request with a nonblank comment.
   - Expect `200`, `ChangesRequested`, and a persisted comment.
4. Request changes without a nonblank comment.
   - Expect `400 VALIDATION_FAILED`; verify the request stays `PendingReview`.
5. Remove the Reviewer role from a user, then retry their pending approval.
   - Expect `403 AUTHORIZATION_DENIED` on the first request after revocation.
6. Re-run a previously successful approval.
   - Expect `409 INVALID_WORKFLOW`; verify no second transition.

### Changes Requested and Resubmission

1. As the Requester, edit owned `ChangesRequested` content.
   - Expect `200` and unchanged `ChangesRequested` status.
2. Submit without changing content since the latest review.
   - Expect `409 INVALID_WORKFLOW`; verify status, version, revisions, and history are
     unchanged.
3. Change at least one content field, then submit.
   - Expect `200` and `PendingReview`; verify the previous reviewed revision and
     comment remain in history.
4. Try to edit or submit an `Approved` request.
   - Expect `409 INVALID_WORKFLOW`; verify content, status, version, and history remain
     immutable.

### Concurrency

1. Load one request through two independent clients or SQLAlchemy sessions with the
   same ETag.
2. Issue two content changes or workflow decisions concurrently.
3. Expect exactly one success.
4. Expect the other attempt to return `409 CONCURRENCY_CONFLICT` with the current
   version in the Problem Details body.
5. Reload persisted state and history; verify no lost update, duplicate transition, or
   partially written revision.

### Deletion

1. Send DELETE for a Draft, PendingReview, ChangesRequested, or Approved request.
   - Expect `405 DELETION_NOT_SUPPORTED`.
2. Verify the request still exists with unchanged content, status, version, and history.

## Acceptance Evidence

For final acceptance, record:

- Commands executed and complete pass/fail output.
- Requirement-to-test mapping covering FR-001 through FR-029 and SC-001 through
  SC-015.
- Persisted-state evidence for create, edit, submit, approve, request changes,
  resubmission, concurrency, role revocation, and deletion rejection.
- Confirmation that generated OpenAPI and contract tests match
  [contracts/openapi.json](contracts/openapi.json).
- Confirmation that no request ID, role, or requester ID supplied by a client was
  trusted as identity or permission.

A successful build or green happy-path tests alone do not satisfy acceptance.
