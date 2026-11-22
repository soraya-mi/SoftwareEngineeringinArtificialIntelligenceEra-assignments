# Acceptance Evidence

**Feature**: `001-change-request-workflow`

**Validated**: 2026-11-22

**Environment**: Windows, Python 3.12.6, isolated `.venv`

## Validation Commands

```powershell
.\.venv\Scripts\ruff.exe check src tests
.\.venv\Scripts\mypy.exe src
$env:CHANGEFLOW_JWT_ISSUER = "https://issuer.test/"
$env:CHANGEFLOW_JWT_AUDIENCE = "changeflow-api"
$env:CHANGEFLOW_JWT_JWKS_URL = "https://issuer.test/jwks"
.\.venv\Scripts\python.exe -m pytest --cov=changeflow --cov-report=term-missing
$env:CHANGEFLOW_DATABASE_URL = "sqlite:///<temporary-db>"
.\.venv\Scripts\alembic.exe upgrade head
```

## Results

| Check | Result |
|-------|--------|
| Ruff | PASS — no violations |
| mypy | PASS — 44 source files, no issues |
| pytest | PASS — 55 tests |
| Coverage | 88% overall statement/branch coverage |
| Alembic | PASS — empty SQLite upgraded to revision `0001` |
| OpenAPI conformance | PASS — operation IDs, error-code enum, Problem Details responses, If-Match, and ETag definitions match the checked-in contract |

## Requirement Evidence

| Requirement area | Evidence |
|------------------|----------|
| Authentication and current roles | JWT verifier tests cover valid identity, bad signature, issuer, audience, expiration, missing subject, and JWKS failure. Provisioning tests cover active, dual-role, replacement, and revocation behavior. |
| Draft create/edit/submit | Domain, API contract, and persisted-state tests verify ownership, normalization, Draft editing, submission, revision creation, transition creation, duplicate rejection, and If-Match behavior. |
| Review approval and request changes | API and persistence tests verify approval by another Reviewer, self-approval denial for dual-role users, own-request request-changes, mandatory feedback, and exact persisted comment text. |
| ChangesRequested revision | API and persistence tests verify unchanged-content rejection, successful changed-content resubmission, and preservation of prior reviewed content and feedback. |
| Approved immutability | API tests verify edits to Approved requests return `409 INVALID_WORKFLOW` without changing approved state. |
| Request and history visibility | Access-policy and API tests verify Requester ownership, pending-review visibility, prior-reviewer access, and denial for unrelated users. |
| Concurrency and atomicity | Real SQLite sessions preload the same request and version; exactly one write succeeds, the stale write raises a concurrency conflict, and forced transition failure rolls the request state back. |
| Deletion exclusion | API tests verify DELETE returns `405 DELETION_NOT_SUPPORTED` and preserves the request. |
| Error safety | Tests verify validation/authentication responses do not echo submitted secrets or tokens. |
| Convergence verification | Repeated approval, JWKS failure, rejected-feedback persistence, approved edit/submit immutability, API token failures, and complete OpenAPI response metadata are tested. |

## API Scenarios Verified

- `POST /api/change-requests`
- `GET /api/change-requests`
- `GET /api/change-requests/{requestId}`
- `PUT /api/change-requests/{requestId}/content`
- `POST /api/change-requests/{requestId}/submit`
- `POST /api/change-requests/{requestId}/approve`
- `POST /api/change-requests/{requestId}/request-changes`
- `GET /api/change-requests/{requestId}/history`
- `DELETE /api/change-requests/{requestId}` returns the required 405 rejection

## External Identity Provider Note

The live OIDC token-acquisition flow is outside this feature. JWT validation is tested
with locally generated RSA keys and a deterministic signing-key resolver. Deployment
must configure a real issuer, audience, and JWKS endpoint and provision matching
server-side user/role records.

## Deviations

None. All implemented behavior traces to an approved requirement in `spec.md`.
