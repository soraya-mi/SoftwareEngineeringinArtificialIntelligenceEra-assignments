# Implementation Plan: Change Request Review Workflow

**Branch**: `001-change-request-workflow` | **Date**: 2026-11-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-change-request-workflow/spec.md`

## Summary

Build a backend-only HTTP API for the ChangeFlow lifecycle. The API will authenticate
users, resolve their current roles from server-side state, create and edit owned
requests, submit them for review, approve them, request changes with mandatory
feedback, and return request/history data without exposing it to unauthorized users.

The implementation will use Python 3.12, FastAPI, SQLAlchemy 2, and SQLite. JWT
bearer authentication establishes caller identity; a server-side user/role store
supplies current authorization. Business decisions remain in framework-independent
Domain and Application packages. Mutations use ETag/If-Match optimistic concurrency,
and request, revision, and transition-history changes commit in one transaction.

## Technical Context

**Language/Version**: Python 3.12.6, the installed runtime; project requires Python `>=3.12,<3.13`

**Primary Dependencies**: FastAPI, Uvicorn, Pydantic 2, pydantic-settings, SQLAlchemy 2,
Alembic, PyJWT with cryptography support, HTTPX, pytest, Ruff, and mypy

**Storage**: SQLite through SQLAlchemy 2 for local delivery and tests, with Alembic
migrations and relational constraints

**Testing**: pytest; FastAPI/Starlette TestClient for API integration; SQLAlchemy
temp-file SQLite databases for persistence and competing-session concurrency tests;
Ruff and mypy for static validation

**Target Platform**: Cross-platform Python service on Windows or Linux; local
development uses Uvicorn and a SQLite file

**Project Type**: Backend web service; no frontend

**Performance Goals**: Not specified in the approved feature scope.

**Constraints**: Python 3.12.6 is installed; FastAPI dependencies are not yet installed.
SQLite has no built-in row-version column, so SQLAlchemy must manage a UUID version
token. Field maximum lengths and content formats are not approved and must not be
invented. The service authenticates callers but does not provide public user, credential,
or role-administration endpoints.

**Scale/Scope**: Single assignment-scale backend API. No production throughput or load
target is approved.

## Constitution Check

*GATE: Evaluated before Phase 0 and re-checked after Phase 1 design.*

Constitution version: **2.0.0**

| Principle | Gate result | Planning evidence |
|-----------|-------------|-------------------|
| I. Specification Before Implementation | PASS | The Project owner approved the specification and plan on 2026-11-22. Every planned behavior maps to FR-001 through FR-029; no clarification markers or open questions remain. |
| II. Architecture and Separation of Concerns | PASS | Domain owns invariants and transitions; Application owns use-case orchestration and current-role authorization; Infrastructure owns SQLAlchemy persistence and role retrieval; API owns HTTP mapping only. |
| III. Security and Authorization | PASS | Every endpoint requires JWT authentication. Identity comes from the validated `sub` claim, while current roles come from server-side state. Self-approval has an explicit denial path and negative test. |
| IV. Business Rule Integrity | PASS | One aggregate transition matrix covers all allowed states. Content revisions and transition records preserve history; Approved is immutable; invalid and repeated actions are rejected. |
| V. Concurrency and Data Integrity | PASS | Every mutable request has a SQLAlchemy-managed UUID version token. Mutations require its ETag, and `StaleDataError` maps to a concurrency conflict without automatic retry or merge. |
| VI. Testing and Validation | PASS | Transition, authorization, persistence, atomicity, and concurrency tests are required, including dual-role self-approval and SQLite-backed persisted-state verification. |
| VII. API and Error Handling | PASS | RFC 7807-style Problem Details responses distinguish authentication, authorization, validation, invalid workflow, and concurrency outcomes without internal exception details. |
| VIII. Scope Control | PASS | The plan is backend-only. AI, frontend, request deletion, user administration, external change execution, and unrelated features are excluded. |

**Initial gate decision**: PASS. No constitutional violation or deviation is requested.

## Project Structure

### Documentation (this feature)

```text
specs/001-change-request-workflow/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── openapi.json
└── checklists/
    └── requirements.md
```

`tasks.md` is intentionally not created by `$speckit-plan`.

### Source Code (repository root)

```text
pyproject.toml
requirements.lock
requirements-dev.lock
alembic.ini
README.md
src/
└── changeflow/
    ├── domain/
    │   └── change_requests/
    │       ├── entities.py
    │       ├── enums.py
    │       ├── errors.py
    │       └── values.py
    ├── application/
    │   ├── ports/
    │   │   ├── change_request_repository.py
    │   │   ├── current_user_role_store.py
    │   │   ├── request_access_policy.py
    │   │   └── unit_of_work.py
    │   ├── change_requests/
    │   │   ├── create.py
    │   │   ├── edit_content.py
    │   │   ├── submit.py
    │   │   ├── approve.py
    │   │   ├── request_changes.py
    │   │   └── queries.py
    │   └── errors.py
    ├── infrastructure/
    │   ├── auth/
    │   │   ├── current_user_role_store.py
    │   │   └── jwt_verifier.py
    │   ├── config.py
    │   ├── persistence/
    │   │   ├── database.py
    │   │   ├── mappings.py
    │   │   ├── repositories.py
    │   │   └── unit_of_work.py
    │   └── migrations/
    │       └── versions/
    ├── cli/
    │   └── provision_user.py
    └── api/
        ├── dependencies.py
        ├── error_handlers.py
        ├── main.py
        ├── schemas.py
        └── routes/
            └── change_requests.py
tests/
├── unit/
│   ├── domain/
│   ├── application/
│   └── infrastructure/
├── integration/
│   ├── api/
│   ├── persistence/
│   └── concurrency/
└── architecture/
```

**Structure Decision**: The source uses a single installable Python package with
explicit Domain, Application, Infrastructure, and API subpackages. This preserves
inward dependency direction without creating unnecessary distribution packages.
There is no frontend.

## Implementation Approach

### Domain

- Model `ChangeRequest` as the transition boundary with current content, status,
  requester, latest reviewed revision, and concurrency token.
- Implement the exact FR-013 transition matrix. Reject unknown, repeated, missing, or
  out-of-state actions.
- Enforce self-approval denial, Approved immutability, title/description/reason
  normalization, and the ChangesRequested revision rule.
- Create immutable content revisions on submission. A Request changes decision
  references the revision reviewed; resubmission compares current content with that
  revision.
- Keep Domain free of FastAPI, Pydantic request schemas, SQLAlchemy, JWT, and HTTP
  status codes.

### Application

- Resolve the caller's active account and current roles on every protected operation.
- Apply request visibility rules: Requesters see owned requests; Reviewers see other
  users' PendingReview requests and requests they previously reviewed.
- Orchestrate create, content edit, submit, approve, request-changes, list, detail,
  and history use cases in plain Python services.
- Convert domain outcomes to explicit Application results. Do not catch failures and
  continue as success.
- Parse the expected version from If-Match in the API adapter and pass it into the
  use case; retain the database version check for the final write race.

### Infrastructure

- Implement typed pydantic-settings configuration in
  `src/changeflow/infrastructure/config.py`, validating required database and JWT
  settings before serving requests.
- Define SQLAlchemy 2 declarative mappings independently of Domain entities.
- Apply Alembic migrations with foreign keys, unique role assignments, transition
  indexes, and the `(request_id, revision_number)` uniqueness rule.
- Configure an application-managed UUID `version_id_col` on the Change Request
  mapping. SQLAlchemy then emits version-checked UPDATEs and raises `StaleDataError`
  when another transaction changed the row.
- Store active users and role assignments locally so role revocation affects the next
  protected operation even when an existing JWT remains valid.
- Provide an operator-facing provisioning command in
  `src/changeflow/cli/provision_user.py`; do not expose user or role administration
  through the public HTTP API.
- Save current request state, content revision, and transition record in one
  transaction. Do not retry stale writes or merge conflicting changes.

### API

- Use FastAPI routers and dependencies with the routes in
  `contracts/openapi.json`.
- Validate protocol shape with Pydantic 2 models, but keep workflow decisions in
  Domain/Application.
- Validate JWT signature, issuer, audience, and lifetime using configured OIDC/JWKS
  metadata. Treat `sub` only as identity.
- Require If-Match for content and transition mutations. Emit a quoted UUID ETag in
  responses.
- Do not expose requester ID or status as accepted create/update fields.
- Do not expose a delete operation; a DELETE request receives a documented 405
  response.
- Override validation and application exception handlers to emit RFC 7807-style
  Problem Details with stable `code` values and no stack traces or internal details.

### Verification

- Domain: exhaustive allowed/denied transitions, immutability, validation, revision
  comparison, and history creation.
- Application: visibility, role revocation, self-approval, reviewer history access,
  and current-role checks.
- Infrastructure: transaction rollback, SQLAlchemy version behavior, persisted
  revisions/history, and competing sessions.
- API integration: every contract status, authentication-negative path,
  authorization-negative path, duplicate action, stale ETag, approved mutation, and
  deletion rejection against a temporary SQLite file.
- Architecture: import analysis confirms Domain/Application do not import API,
  FastAPI, Pydantic request schemas, SQLAlchemy, or JWT libraries; API routes do not
  contain workflow transitions.

## Post-Design Constitution Check

| Principle | Result | Post-design evidence |
|-----------|--------|----------------------|
| I. Specification Before Implementation | PASS | `data-model.md`, `contracts/openapi.json`, and `quickstart.md` trace to approved requirements without adding product behavior. |
| II. Architecture and Separation of Concerns | PASS | Package dependencies point inward: Infrastructure/API depend on Application; Domain/Application are framework-independent. |
| III. Security and Authorization | PASS | JWT identity and server-side current-role lookup are explicit for every route. Self-approval is separately denied and tested. |
| IV. Business Rule Integrity | PASS | Transition matrix, revision snapshots, comments, and immutable Approved state align across spec, model, and contract. |
| V. Concurrency and Data Integrity | PASS | ETag/If-Match, SQLAlchemy `version_id_col`, one transaction per mutation, and `StaleDataError` mapping cover edits and transitions. |
| VI. Testing and Validation | PASS | The validation guide and test layers cover persisted state, rollback, all negative paths, and competing sessions. |
| VII. API and Error Handling | PASS | The OpenAPI contract defines consistent Problem Details and distinct codes for authentication, authorization, workflow, validation, and concurrency. |
| VIII. Scope Control | PASS | No frontend, deletion, user administration, AI, external change execution, or unapproved field constraints appear in the design. |

**Post-design gate decision**: PASS. No complexity exception is required.

## Requirement Traceability

| Planned workstream | Approved requirements |
|--------------------|-----------------------|
| JWT identity, active account, and current server-side roles | FR-001, FR-018, FR-022 |
| Configuration and supported user/role provisioning | FR-001, FR-022 |
| Creation, server-assigned owner, content normalization, and Draft/ChangesRequested editing | FR-002, FR-003, FR-004, FR-005, FR-006, FR-011, FR-028 |
| Draft and revised submission, revision snapshots, and changed-content rule | FR-007, FR-012, FR-021, FR-027 |
| Approval, self-approval denial, and Request changes | FR-008, FR-009, FR-010, FR-025 |
| Complete transition matrix, Approved immutability, and invalid/repeated action rejection | FR-013, FR-014, FR-015, FR-019 |
| Transition-time identity, role, relationship, and state validation | FR-016, FR-018 |
| ETag precondition, optimistic concurrency, conflict mapping, and atomic transactions | FR-017, FR-026 |
| Accepted-transition history and immutable review feedback | FR-020, FR-021, FR-025 |
| Request, history, and feedback visibility | FR-023, FR-025, FR-029 |
| No-deletion behavior | FR-024 |
| Problem Details distinction and sensitive-error redaction | FR-022 |
| Required transition, authorization, persistence, and concurrency tests | SC-001 through SC-015 |

## Complexity Tracking

No constitutional violations or deviations require justification.
