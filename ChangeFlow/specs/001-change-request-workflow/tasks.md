# Tasks: Change Request Review Workflow

**Input**: Design documents from `specs/001-change-request-workflow/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/openapi.json](contracts/openapi.json), [quickstart.md](quickstart.md)

**Tests**: Included because the specification defines measurable acceptance outcomes
and the ChangeFlow Constitution requires automated tests for every business and
authorization rule. Story tests MUST be written first and observed failing before
their implementation tasks.

**Organization**: Tasks are grouped by user story so each story can be implemented
and verified independently after the shared foundation is complete.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it changes different files and has no dependency
  on another incomplete task in the same batch.
- **[Story]**: Required only for user-story tasks and maps to `spec.md`.
- Every task names an exact file path and the requirements it advances.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Initialize the Python project without adding product behavior.

- [X] T001 Create the package and test directory tree from `plan.md`, including `src/changeflow/domain/change_requests/`, `src/changeflow/application/`, `src/changeflow/infrastructure/`, `src/changeflow/cli/`, `src/changeflow/api/`, `tests/unit/infrastructure/`, and `tests/integration/persistence/` (supports FR-001 through FR-029)
- [X] T002 Define Python 3.12 project metadata and pinned runtime dependencies in `pyproject.toml`, then generate and commit exact versions in `requirements.lock` and `requirements-dev.lock` (supports FR-022 and constitution dependency controls)
- [X] T003 Configure Ruff, mypy, pytest paths, markers, and coverage settings in `pyproject.toml` so later tests can prove SC-001 through SC-015
- [X] T004 [P] Write failing configuration-validation tests for required database, JWT issuer, audience, JWKS URL, and environment settings in `tests/unit/infrastructure/test_config.py`, then implement the pydantic-settings object in `src/changeflow/infrastructure/config.py` and document non-secret variables in `.env.example` (FR-001, FR-022)
- [X] T005 [P] Configure Alembic database URL loading and migration discovery in `alembic.ini` and `src/changeflow/infrastructure/migrations/env.py` (supports FR-004, FR-020, and FR-026)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish shared Domain, persistence, identity, API, and test infrastructure.

**CRITICAL**: User-story implementation must not begin until T006 through T021 pass.

- [X] T006 Implement the canonical status/action/role enums and normalized content value object in `src/changeflow/domain/change_requests/enums.py` and `src/changeflow/domain/change_requests/values.py`, enforcing that title, description, and reason are nonempty after trimming (FR-004, FR-013, FR-028)
- [X] T007 [P] Implement typed Domain and Application exceptions for validation, authorization, self-approval, invalid workflow, and concurrency in `src/changeflow/domain/change_requests/errors.py` and `src/changeflow/application/errors.py` (FR-009, FR-022, FR-026)
- [X] T008 Create SQLAlchemy `UserAccount` and `UserRoleAssignment` mappings in `src/changeflow/infrastructure/persistence/mappings.py` with active-user state and unique `(user_id, role)` assignments (FR-001, FR-018)
- [X] T009 Create SQLAlchemy `ChangeRequest`, `ChangeRequestRevision`, and `ChangeRequestTransition` mappings in `src/changeflow/infrastructure/persistence/mappings.py`, including the UUID `version_id_col`, required fields, enum values, nullable latest-reviewed revision, and immutable history fields (FR-004, FR-013, FR-017, FR-020, FR-021)
- [X] T010 [P] Implement the engine, request-scoped SQLAlchemy session factory, and transaction unit of work in `src/changeflow/infrastructure/persistence/database.py` and `src/changeflow/infrastructure/persistence/unit_of_work.py` (FR-017, FR-026)
- [X] T011 Generate the initial Alembic migration in `src/changeflow/infrastructure/migrations/versions/0001_initial.py` with foreign keys, unique role/revision constraints, transition indexes, and non-null version/comment rules (FR-004, FR-017, FR-020, FR-025, FR-026)
- [X] T012 [P] Write failing JWT verifier tests for valid identity, bad signature, wrong issuer, wrong audience, expired token, missing `sub`, and JWKS failure in `tests/unit/infrastructure/test_jwt_verifier.py` (FR-001, FR-022)
- [X] T013 [P] Implement JWT signature, issuer, audience, lifetime, and `sub` validation in `src/changeflow/infrastructure/auth/jwt_verifier.py`, relying on configured JWKS metadata and returning only authenticated identity (FR-001, FR-022)
- [X] T014 [P] Implement the server-side active user/current-role store in `src/changeflow/infrastructure/auth/current_user_role_store.py` so role revocation applies to the next operation (FR-001, FR-018)
- [X] T015 Write failing user/role provisioning tests for active-user, Requester, Reviewer, dual-role, role-revocation, and duplicate-role behavior in `tests/integration/persistence/test_user_provisioning.py`, then implement the operator-facing command in `src/changeflow/cli/provision_user.py` (FR-001, FR-018)
- [X] T016 [P] Implement Problem Details exception handlers and stable error-code mapping in `src/changeflow/api/error_handlers.py`, including redaction of internal details and application of `application/problem+json` (FR-022)
- [X] T017 [P] Implement the quoted-UUID ETag/If-Match parser dependency in `src/changeflow/api/dependencies.py`, returning `428 PRECONDITION_REQUIRED` for a missing or malformed precondition (FR-017)
- [X] T018 Implement the FastAPI application factory, validated settings wiring, authentication dependency, router registration, and `/api` prefix in `src/changeflow/api/main.py` and `src/changeflow/api/routes/__init__.py` (FR-001 through FR-029)
- [X] T019 Create temp-file SQLite and app dependency-override fixtures in `tests/conftest.py` so integration tests exercise real persistence without sharing in-memory state (FR-001 through FR-029)
- [X] T020 Create current-user and role-assignment fixtures in `tests/conftest.py` and `tests/integration/api/auth_helpers.py` supporting authenticated users, revoked roles, and users with both roles (FR-001, FR-009, FR-018)
- [X] T021 [P] Add import-boundary architecture tests in `tests/architecture/test_import_boundaries.py` that prohibit Domain/Application imports of FastAPI, Pydantic API schemas, SQLAlchemy, or JWT libraries (supports FR-001 through FR-029 and the architecture gate in `plan.md`)

**Checkpoint**: The project can start, authenticate a test caller, load current roles,
open a migrated SQLite database, emit contract-shaped errors, and run shared fixtures.

---

## Phase 3: User Story 1 - Create, edit, and submit a Draft request (Priority: P1) MVP

**Goal**: A current Requester creates, reads, edits, and submits their own Draft while
other users cannot modify it and deletion remains unsupported.

**Independent Test**: Using a migrated database and test JWT, create a request as one
Requester, verify server-assigned ownership and `Draft`, edit it with its current ETag,
submit it to `PendingReview`, verify persisted revision/history, and prove another
Requester cannot edit, submit, or delete it.

### Tests for User Story 1

- [X] T022 [P] [US1] Write failing Domain tests for trimming, required content, Draft creation, owner edits, and non-owner edit denial in `tests/unit/domain/test_request_creation_and_editing.py` (FR-002 through FR-006, FR-028; SC-005, SC-013)
- [X] T023 [P] [US1] Write failing Domain tests for Draft submission, immutable revision snapshot, Submit transition history, duplicate submission, and invalid source states in `tests/unit/domain/test_draft_submission.py` (FR-007, FR-013, FR-014, FR-019, FR-020; SC-001, SC-007, SC-014)
- [X] T024 [P] [US1] Write failing API contract tests for create, list, detail, history, content update, and submit operations in `tests/integration/api/test_us1_create_edit_submit_contract.py` (FR-002 through FR-007, FR-013, FR-019, FR-020, FR-022, FR-029)
- [X] T025 [P] [US1] Write failing API authorization tests for unauthenticated access, invalid signature, wrong issuer, wrong audience, expired token, unknown/inactive user, spoofed requester ID, non-owner access, own visibility, and DELETE rejection in `tests/integration/api/test_us1_access_and_delete.py` (FR-001, FR-006, FR-018, FR-023, FR-024; SC-005, SC-006, SC-011)
- [X] T026 [US1] Write a failing persisted-state integration test proving create/edit/submit store normalized content, one revision, one transition, and no partial records in `tests/integration/persistence/test_us1_persistence.py` (FR-004, FR-007, FR-020, FR-026; SC-007, SC-009)

### Implementation for User Story 1

- [X] T027 [P] [US1] Implement `ChangeRequest` creation, content editing, owner checks, Draft constraints, timestamps, and version initialization in `src/changeflow/domain/change_requests/entities.py` (FR-002 through FR-006, FR-028)
- [X] T028 [US1] Implement Draft submission, revision-number assignment, revision snapshots, accepted-transition creation, and duplicate/invalid transition denial in `src/changeflow/domain/change_requests/entities.py` (FR-007, FR-013, FR-014, FR-019 through FR-021)
- [X] T029 [P] [US1] Define repository and unit-of-work interfaces for request creation, content reads/writes, revisions, transitions, and visibility queries in `src/changeflow/application/ports/change_request_repository.py` and `src/changeflow/application/ports/unit_of_work.py` (FR-004, FR-020, FR-023, FR-026)
- [X] T030 [US1] Implement SQLAlchemy repository methods for create, content update, request lookup, revisions, and transition persistence in `src/changeflow/infrastructure/persistence/repositories.py` (FR-004, FR-007, FR-020, FR-026)
- [X] T031 [P] [US1] Implement the create use case with current Requester-role enforcement and server-assigned owner in `src/changeflow/application/change_requests/create.py` (FR-001 through FR-003)
- [X] T032 [P] [US1] Implement the content-edit use case for owned Draft requests in `src/changeflow/application/change_requests/edit_content.py` (FR-005, FR-006, FR-028)
- [X] T033 [P] [US1] Implement the submit use case for owned Draft requests with current Requester-role enforcement in `src/changeflow/application/change_requests/submit.py` (FR-001, FR-007, FR-016, FR-018)
- [X] T034 [US1] Implement own-request list/detail/history queries and initial access policy in `src/changeflow/application/change_requests/queries.py` and `src/changeflow/application/ports/request_access_policy.py` (FR-020, FR-023, FR-029)
- [X] T035 [P] [US1] Define Pydantic create/update/request/response/list/history schemas without editable requester ID or status fields in `src/changeflow/api/schemas.py` (FR-002 through FR-007, FR-022, FR-023)
- [X] T036 [US1] Implement GET list, POST create, GET detail, GET history, and DELETE-rejection routes with ETag and Problem Details responses in `src/changeflow/api/routes/change_requests.py` (FR-001 through FR-007, FR-020, FR-022 through FR-024, FR-029)
- [X] T037 [US1] Implement PUT content and POST submit routes with If-Match propagation and quoted ETag responses in `src/changeflow/api/routes/change_requests.py` (FR-005, FR-007, FR-017, FR-022)

**Checkpoint**: User Story 1 is independently functional and testable; it is the MVP.

---

## Phase 4: User Story 2 - Review a pending request (Priority: P1)

**Goal**: A current Reviewer views eligible pending requests, approves another user's
request, and requests changes with mandatory feedback. Self-approval is impossible,
and Reviewer visibility/history access follows the clarified policy.

**Independent Test**: Seed `PendingReview` requests created by other users, authenticate
a Reviewer, approve one, request changes on another with a comment, verify visibility
and history, deny a dual-role owner's self-approval, revoke the Reviewer role, and prove
the next decision is denied.

### Tests for User Story 2

- [X] T038 [P] [US2] Write failing Domain tests for approval, request-changes comment requirements, self-approval denial, own-request request-changes, and invalid review states in `tests/unit/domain/test_review_transitions.py` (FR-008 through FR-013, FR-019, FR-025; SC-001, SC-002, SC-010, SC-014)
- [X] T039 [P] [US2] Write failing Application tests for current-role lookup, role revocation, pending-request visibility, prior-reviewed access, and history inheritance in `tests/unit/application/test_review_authorization.py` (FR-001, FR-018, FR-023, FR-025, FR-029; SC-006, SC-015)
- [X] T040 [P] [US2] Write failing API contract tests for list visibility, approve, request changes, missing comments, self-approval, and repeated review actions in `tests/integration/api/test_us2_review_contract.py` (FR-008 through FR-013, FR-019, FR-022 through FR-025)
- [X] T041 [US2] Write failing persisted-state tests proving comments and review transitions are immutable, failed reviews write nothing, and role revocation takes effect immediately in `tests/integration/persistence/test_us2_review_persistence.py` (FR-009, FR-018, FR-020, FR-021, FR-025, FR-026)

### Implementation for User Story 2

- [X] T042 [US2] Implement approval and request-changes aggregate methods, nonblank-after-trim comment validation with original-text persistence, reviewed-revision linkage, and accepted transition records in `src/changeflow/domain/change_requests/entities.py` (FR-008 through FR-013, FR-020, FR-021, FR-025)
- [X] T043 [US2] Extend the access policy for other users' PendingReview requests and requests with a prior review decision by the caller in `src/changeflow/application/ports/request_access_policy.py` and `src/changeflow/application/change_requests/queries.py` (FR-023, FR-029)
- [X] T044 [P] [US2] Implement the approve use case with current Reviewer-role and non-owner enforcement in `src/changeflow/application/change_requests/approve.py` (FR-001, FR-008, FR-009, FR-016, FR-018)
- [X] T045 [P] [US2] Implement the request-changes use case allowing the owner as Reviewer, requiring nonblank-after-trim feedback, and preserving the original comment text in `src/changeflow/application/change_requests/request_changes.py` (FR-001, FR-010, FR-016, FR-018, FR-025)
- [X] T046 [US2] Add SQLAlchemy visibility queries for eligible pending requests and prior review participation in `src/changeflow/infrastructure/persistence/repositories.py` (FR-023, FR-029)
- [X] T047 [US2] Add approve and request-changes Pydantic request/response support in `src/changeflow/api/schemas.py` (FR-022, FR-025)
- [X] T048 [US2] Implement approve and request-changes routes with If-Match, ETag, and exact workflow responses in `src/changeflow/api/routes/change_requests.py` (FR-008 through FR-013, FR-017, FR-022, FR-025)
- [X] T049 [US2] Map self-approval and review-state failures to distinct Problem Details `code` values in `src/changeflow/api/error_handlers.py` (FR-009, FR-022)
- [X] T050 [US2] Implement history responses containing actor, action, prior/current state, occurrence time, comment, and reviewed revision in `src/changeflow/api/schemas.py` and `src/changeflow/application/change_requests/queries.py` (FR-020, FR-021, FR-025, FR-029)
- [X] T051 [US2] Add end-to-end review acceptance tests covering approval, request changes, own-request request-changes, self-approval denial, role revocation, and Reviewer list/history visibility in `tests/integration/api/test_us2_review_acceptance.py` (FR-008 through FR-010, FR-018, FR-023, FR-025, FR-029; SC-002, SC-006, SC-010, SC-015)

**Checkpoint**: Pending requests can be reviewed independently after seeding their
state; rejected actions leave persisted state and history unchanged.

---

## Phase 5: User Story 3 - Revise a request after changes are requested (Priority: P2)

**Goal**: A Requester revises their own `ChangesRequested` content and resubmits only
after a meaningful content change while preserving the previously reviewed revision
and feedback.

**Independent Test**: Seed a `ChangesRequested` request with a reviewed revision and
comment, edit it as its owner, prove unchanged content cannot resubmit, change one
field, resubmit to `PendingReview`, and verify prior content/comment/history remain.

### Tests for User Story 3

- [X] T052 [P] [US3] Write failing Domain tests for normalized content comparison, unchanged resubmission denial, changed-field resubmission, and non-owner denial in `tests/unit/domain/test_changes_requested_revision.py` (FR-011, FR-012, FR-021, FR-027; SC-012)
- [X] T053 [P] [US3] Write failing API contract tests for editing, unchanged resubmission, changed resubmission, and Approved immutability with exact ETags in `tests/integration/api/test_us3_revision_contract.py` (FR-011, FR-012, FR-015, FR-017, FR-022, FR-027)
- [X] T054 [US3] Write failing persisted-state/history tests proving prior reviewed content and comments survive edit and resubmission in `tests/integration/persistence/test_us3_revision_history.py` (FR-020, FR-021, FR-025, FR-027; SC-007, SC-012)

### Implementation for User Story 3

- [X] T055 [P] [US3] Extend Domain editing so owners may update only `ChangesRequested` content while preserving status and normalized validation in `src/changeflow/domain/change_requests/entities.py` (FR-011, FR-028)
- [X] T056 [US3] Extend Domain submission with normalized comparison against the revision referenced by `LatestReviewedRevisionId` and reject unchanged content in `src/changeflow/domain/change_requests/entities.py` (FR-012, FR-021, FR-027)
- [X] T057 [US3] Extend the content-edit use case to allow owned `ChangesRequested` requests with current Requester-role enforcement in `src/changeflow/application/change_requests/edit_content.py` (FR-001, FR-011, FR-016, FR-018)
- [X] T058 [US3] Extend the submit use case to allow only changed `ChangesRequested` content and create the next revision atomically in `src/changeflow/application/change_requests/submit.py` (FR-012, FR-016, FR-026, FR-027)
- [X] T059 [US3] Extend repository reads/writes for latest reviewed revision and sequential revision creation in `src/changeflow/infrastructure/persistence/repositories.py` (FR-020, FR-021, FR-027)
- [X] T060 [US3] Update response/history serialization to expose the reviewed revision while retaining all prior feedback in `src/changeflow/api/schemas.py` (FR-020, FR-021, FR-025, FR-029)
- [X] T061 [US3] Add an independent API acceptance test that seeds ChangesRequested state, exercises edit/resubmit, and proves prior comments/revisions remain visible in `tests/integration/api/test_us3_revision_acceptance.py` (FR-011, FR-012, FR-020, FR-021, FR-025, FR-027; SC-007, SC-012)
- [X] T062 [US3] Verify Approved edit/submit attempts return `409 INVALID_WORKFLOW` without version, content, status, revision, or history changes in `tests/integration/api/test_us3_approved_immutability.py` (FR-015, FR-026; SC-004, SC-009)

**Checkpoint**: The full revision loop works without depending on live Review UI code;
the test fixture supplies the prior review decision.

---

## Phase 6: User Story 4 - Protect workflow integrity during concurrent actions (Priority: P2)

**Goal**: Optimistic concurrency prevents lost updates or competing workflow decisions,
and failed mutations leave no partial database changes.

**Independent Test**: Load the same request through two independent SQLAlchemy sessions,
attempt edits or review decisions with the same ETag, prove exactly one commit succeeds,
the other returns `409 CONCURRENCY_CONFLICT`, and persisted state/history reflect only
the successful operation.

### Tests for User Story 4

- [X] T063 [P] [US4] Write failing two-session content-update races in `tests/integration/concurrency/test_content_update_race.py`, proving one update wins, the stale update raises `StaleDataError`, and the winner is persisted (FR-017, FR-026; SC-003, SC-009)
- [X] T064 [P] [US4] Write failing competing-review races in `tests/integration/concurrency/test_review_decision_race.py`, proving only one approval/request-changes transition commits (FR-013, FR-017, FR-019, FR-026; SC-001, SC-003, SC-014)
- [X] T065 [P] [US4] Write failing atomic-rollback tests that force revision or transition persistence failure and prove request state is fully rolled back in `tests/integration/concurrency/test_atomic_rollback.py` (FR-020, FR-026; SC-009)
- [X] T066 [P] [US4] Write failing API contract tests for missing If-Match, stale ETag, `CONCURRENCY_CONFLICT`, and `currentVersion` in `tests/integration/api/test_us4_concurrency_contract.py` (FR-017, FR-022, FR-026; SC-003, SC-009)

### Implementation for User Story 4

- [X] T067 [US4] Finalize SQLAlchemy version assignment and concurrency mappings on all mutable request writes in `src/changeflow/infrastructure/persistence/mappings.py` (FR-017)
- [X] T068 [US4] Catch `StaleDataError`, roll back the unit of work, and translate it to a concurrency outcome without retry in `src/changeflow/infrastructure/persistence/unit_of_work.py` (FR-017, FR-022, FR-026)
- [X] T069 [US4] Enforce one transaction around request state, revision, and transition changes in `src/changeflow/application/change_requests/edit_content.py`, `src/changeflow/application/change_requests/submit.py`, `src/changeflow/application/change_requests/approve.py`, and `src/changeflow/application/change_requests/request_changes.py` (FR-017, FR-020, FR-026)
- [X] T070 [US4] Add `409 CONCURRENCY_CONFLICT` Problem Details with `currentVersion` and preserve distinct invalid-workflow mapping in `src/changeflow/api/error_handlers.py` (FR-017, FR-022)
- [X] T071 [US4] Add end-to-end concurrency acceptance tests covering two API clients, stale ETags, final state reload, and history integrity in `tests/integration/api/test_us4_concurrency_acceptance.py` (FR-017, FR-022, FR-026; SC-003, SC-009)

**Checkpoint**: All mutation paths reject stale representations deterministically and
no concurrency failure can leave a partial update.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Validate contract, architecture, security, and delivery evidence.

- [X] T072 [P] Add generated-OpenAPI conformance tests comparing `changeflow.api.main:app.openapi()` operations, schemas, error codes, If-Match, and ETag definitions with `contracts/openapi.json` in `tests/integration/api/test_openapi_conformance.py` (FR-001 through FR-029)
- [X] T073 [P] Document installation, migration, run, test, authentication configuration, and unsupported-deletion behavior in `README.md` (FR-001, FR-024, FR-022)
- [X] T074 [P] Add error-redaction and log-review tests proving validation messages, tokens, stack traces, and internal exception details are not exposed in `tests/integration/api/test_error_redaction.py` (FR-022; SC-009)
- [X] T075 Run Ruff, mypy, all pytest layers, Alembic upgrade from an empty database, and architecture tests from `pyproject.toml`, fixing failures without weakening assertions (SC-001 through SC-015)
- [X] T076 Execute every scenario in `quickstart.md` and record commands, persisted evidence, requirement coverage, deviations, and acceptance status in `docs/acceptance-evidence.md` (FR-001 through FR-029; SC-001 through SC-015)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Starts immediately.
- **Foundational (Phase 2)**: Depends on T001 through T005 and blocks every story.
- **User Story 1 (Phase 3)**: Depends on Phase 2.
- **User Story 2 (Phase 4)**: Depends on Phase 2. Its persisted-state tests seed
  `PendingReview` data, so it does not require live US1 code.
- **User Story 3 (Phase 5)**: Depends on Phase 2 and seeds `ChangesRequested` data.
  Full cross-feature demonstration also uses US1/US2 endpoints after implementation.
- **User Story 4 (Phase 6)**: Depends on Phase 2. It can start alongside US1-US3 once
  shared mappings and transaction boundaries exist.
- **Polish (Phase 7)**: Depends on all desired stories.

```text
T001 -> T002 -> T003/T004/T005
T003/T004/T005 -> T006 -> T007...T021
T006...T021 -> US1 (T022...T037)
T006...T021 -> US2 (T038...T051)
T006...T021 -> US3 (T052...T062)
T006...T021 -> US4 (T063...T071)
US1 + US2 + US3 + US4 -> Polish (T072...T076)
```

### Story Dependency and MVP Notes

- **US1 (P1)**: Standalone MVP after Foundation.
- **US2 (P1)**: Standalone review slice using seeded pending requests.
- **US3 (P2)**: Standalone revision slice using seeded reviewed state; best demonstrated
  end-to-end after US2.
- **US4 (P2)**: Cross-cutting concurrency slice after Foundation; review-race tests
  seed pending state directly.
- **MVP**: Setup + Foundational + US1. Stop at T037 and validate before extending.

### Within Each Story

1. Write and run the listed tests; confirm they fail for the intended missing behavior.
2. Implement Domain behavior.
3. Implement repository/Application behavior.
4. Implement API schemas and routes.
5. Run story tests and persisted-state checks before advancing.

## Parallel Execution Examples

### User Story 1

```text
Parallel test authoring:
- T022 Domain creation/edit tests
- T023 Domain submit tests
- T024 API create/edit/submit contract tests
- T025 API access/delete tests

After those tests and shared ports exist:
- T027 Domain creation/edit behavior
- T029 Repository/unit-of-work interfaces
- T031 Create use case
- T032 Edit use case
- T033 Submit use case
- T035 API schemas
```

### User Story 2

```text
Parallel after Foundation:
- T038 Domain review tests
- T039 Application authorization tests
- T040 API review contract tests

Parallel implementation in separate files:
- T044 Approve use case
- T045 Request-changes use case
```

### User Story 3

```text
Parallel test authoring:
- T052 Domain revision tests
- T053 API revision contract tests

Parallel implementation:
- T057 Edit use-case extension
- T058 Submit use-case extension
```

### User Story 4

```text
Parallel concurrency test authoring:
- T063 Content update race
- T064 Review decision race
- T065 Atomic rollback
- T066 API concurrency contract
```

## Implementation Strategy

### MVP First

1. Complete Setup and Foundational phases.
2. Complete US1 through T037.
3. Stop and validate create/edit/read/submit, ownership, persisted revision/history,
   duplicate rejection, and deletion denial.
4. Demo the API only after tests prove the MVP independently.

### Incremental Delivery

1. Foundation plus US1: requester Draft workflow.
2. Add US2: complete review decisions and Reviewer visibility.
3. Add US3: revision loop and reviewed-history preservation.
4. Add US4: stale-write and competing-decision protection.
5. Run Polish after the desired increment is functionally complete.

### Parallel Team Strategy

After Foundation, one developer may take each story. Coordinate shared-file work in
`src/changeflow/domain/change_requests/entities.py`,
`src/changeflow/infrastructure/persistence/repositories.py`,
`src/changeflow/api/schemas.py`, and
`src/changeflow/api/routes/change_requests.py`; tasks touching those files are
intentionally not parallelized.

## Phase 8: Convergence

- [ ] T077 Add a repeated approval contract test proving an Approved request returns `409 INVALID_WORKFLOW` and creates no additional transition in `tests/integration/api/test_us2_review_contract.py` per FR-019/T040 (partial)
- [ ] T078 Declare success ETag headers and Problem Details error responses in `src/changeflow/api/routes/change_requests.py`, then expand `tests/integration/api/test_openapi_conformance.py` to compare operations, schemas, error codes, If-Match, and ETag definitions with `specs/001-change-request-workflow/contracts/openapi.json` per FR-022/T072 (partial)
- [ ] T079 Add a JWKS resolver failure test proving `JwtVerifier` returns an authentication error in `tests/unit/infrastructure/test_jwt_verifier.py` per FR-001/T012 (partial)
- [ ] T080 Add a persisted-state test proving blank review feedback leaves request version, status, and transition history unchanged in `tests/integration/persistence/test_us2_review_persistence.py` per FR-025/FR-026/T041 (partial)
- [ ] T081 Add tests proving both Approved content edits and Approved submissions return `409 INVALID_WORKFLOW` without changing version, content, status, revisions, or history in `tests/integration/api/test_us3_approved_immutability.py` per FR-015/T062 (partial)
- [ ] T082 Add API authentication-negative tests for expired tokens, wrong issuer/audience, and unknown or inactive users in `tests/integration/api/test_us1_access_and_delete.py` per FR-001/T025 (partial)
