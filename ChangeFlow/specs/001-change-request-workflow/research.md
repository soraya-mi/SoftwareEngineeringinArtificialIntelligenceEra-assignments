# Phase 0 Research: Change Request Review Workflow

**Feature**: `001-change-request-workflow`

## Runtime and Package Management

### Decision

Use the installed Python 3.12.6 runtime and declare Python `>=3.12,<3.13` in
`pyproject.toml`. Use a virtual environment, pinned application/development lock
files, Ruff, and mypy.

### Rationale

Python 3.12 is already available in the workspace, so no runtime installation is
required. A narrow interpreter range avoids compatibility surprises while lock files
preserve reproducible dependency resolution.

### Alternatives considered

- JavaScript on Node.js 22: also installed, but Python keeps the typed Domain model,
  FastAPI validation, SQLAlchemy transaction model, and pytest workflow compact.
- An older Python version: unnecessary when 3.12 is already installed.
- Unpinned package installation: rejected because the constitution requires exact
  dependency versions and lock files when supported.

## HTTP Framework

### Decision

Use FastAPI on Uvicorn with synchronous SQLAlchemy work performed in normal
framework-managed worker threads. Use Pydantic 2 request/response schemas at the API
boundary and custom exception handlers for a consistent Problem Details contract.

### Rationale

FastAPI provides typed OpenAPI generation, dependency injection, bearer security
support, validation, and custom exception handlers without forcing workflow rules into
the transport layer. Synchronous SQLAlchemy keeps the transaction and concurrency
design simple for SQLite and this assignment.

### Alternatives considered

- Flask: requires more manual request validation and OpenAPI wiring.
- Django REST Framework: heavier than needed for one bounded API feature.
- Async SQLAlchemy: adds async session/driver complexity without a demonstrated
  high-concurrency requirement.
- Returning FastAPI's default `{ "detail": ... }` errors: rejected because the
  constitution requires distinguishable error classes and a stable contract.

Sources: [FastAPI SQL databases](https://fastapi.tiangolo.com/tutorial/sql-databases/), [FastAPI error handling](https://fastapi.tiangolo.com/tutorial/handling-errors/)

## Authentication and Current Roles

### Decision

Validate standards-compliant bearer JWT access tokens against configured issuer,
audience, signature/JWKS, and lifetime using PyJWT with cryptography support. Treat
`sub` as caller identity only, then load the active user and current roles from the
server-side database for every protected operation.

### Rationale

The specification requires role revocation to affect subsequent requests. Roles in an
already-issued JWT may be stale. Loading current role assignments makes revocation
effective immediately and prevents clients from asserting user identity or permissions.

### Alternatives considered

- Trust role claims from the JWT: rejected because revocation would wait for token
  expiration or refresh.
- Accept caller user ID in a request body: forbidden by FR-001 and FR-003.
- Add login or user-administration endpoints: outside feature scope.
- Generate password hashes inside ChangeFlow: unnecessary when the API consumes access
  tokens from a configured identity provider.

Source: [FastAPI OAuth2/JWT security](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)

## Persistence and Optimistic Concurrency

### Decision

Use SQLAlchemy 2 with SQLite and Alembic migrations. Configure a UUID
`version_id_col` with a UUID4 generator on the Change Request mapping, expose it as an
ETag, require If-Match for mutations, and map `StaleDataError` to a concurrency
conflict.

### Rationale

SQLAlchemy versioning updates the version value and includes the previously loaded
version in `UPDATE ... WHERE id = ... AND version = ...`. If another transaction
changed the row, zero rows match and SQLAlchemy raises `StaleDataError`. This provides
optimistic concurrency even though SQLite has no native row-version type.

### Alternatives considered

- Last-write-wins updates: violates FR-017.
- Automatic retry or merge: could apply stale intent to a newer state and contradicts
  the requirement to report conflicts.
- SQLite-only locking: does not protect clients that load a representation and submit
  an edit later.
- PostgreSQL `xmin`: useful in production but unnecessary for the assignment-scale
  SQLite implementation.

Source: [SQLAlchemy 2 configuring a version counter](https://docs.sqlalchemy.org/en/20/orm/versioning.html)

## History and Revision Model

### Decision

Persist accepted transition records and immutable content revisions. A successful
submission creates a revision. A Request changes decision references the revision
reviewed and stores the required comment on its transition record. Resubmission
compares current normalized content with that revision.

### Rationale

The feature requires a content change after feedback and requires prior reviewed
content, comments, and workflow history to remain auditable. A revision reference
avoids inferring the reviewed state from mutable request fields.

### Alternatives considered

- Store only current request content: cannot prove what was reviewed.
- Store only a revision number without a snapshot: detects a history change but cannot
  reconstruct reviewed content.
- Serialize all history into one JSON column: weakens relational constraints without an
  approved need.

## Error Contract

### Decision

Register exception handlers for validation, application/domain errors, stale writes,
and generic server errors. Return `application/problem+json` with `title`, `status`,
`detail`, `instance`, and stable extension `code`. Use `currentVersion` only for
concurrency conflicts.

### Rationale

FastAPI supports custom handlers for request validation and application exceptions.
The stable error contract satisfies the requirement to distinguish authentication,
authorization, validation, invalid workflow, and concurrency failures while redacting
internal details.

### Alternatives considered

- Expose exception strings/stack traces: violates the constitution's error-redaction
  requirement.
- Map all 409 outcomes to one code: prevents clients and tests from distinguishing
  stale writes from invalid or repeated workflow actions.

Sources: [FastAPI error handling](https://fastapi.tiangolo.com/tutorial/handling-errors/), [Problem Details RFC 7807](https://www.rfc-editor.org/rfc/rfc7807)

## Testing Strategy

### Decision

Use pytest, FastAPI/Starlette TestClient, SQLAlchemy temp-file SQLite databases,
`pytest-cov`, Ruff, and mypy. Use dependency overrides for deterministic JWT identities
and seed current role assignments through persistence fixtures.

### Rationale

The constitution requires persisted-state verification, real competing updates, and
negative authorization tests. A temporary file database allows independent SQLAlchemy
sessions to compete against the same persistent state and exercise `StaleDataError`.

### Alternatives considered

- SQLite `:memory:` without shared connections: can hide transaction and concurrency
  behavior across sessions.
- Mock-only tests: insufficient for constraints, transaction rollback, or contract
  behavior.
- Browser-based end-to-end tests: unnecessary because the feature has no frontend.

## Scope and Environment Decisions

### Decision

Deliver a backend HTTP API only. Do not implement a frontend, login/token issuance,
user/role administration, request deletion, approved change execution, AI, or content
length/format limits.

### Rationale

Those capabilities are absent from the specification or explicitly excluded by the
constitution. Deletion remains a documented 405 rejection. Required-field and
whitespace rules are the only approved content validation.

### Alternatives considered

- Add a frontend or role-administration API: violates scope control.
- Add hard deletion: rejected by the clarified specification.
- Invent field length limits: not approved.

## Residual Planning Risks

- FastAPI, SQLAlchemy, and test dependencies are not installed yet; implementation
  requires an approved dependency installation step.
- SQLite is suitable for the assignment and persisted concurrency tests but is not a
  production high-write-volume database.
- The external identity provider is configuration-dependent. Token issuance is outside
  this feature, though the API contract assumes callers can obtain valid JWTs.
