<!--
Sync Impact Report
Version change: 1.0.0 -> 2.0.0
Modified principles:
- I. Specification Before Implementation: expanded requirement traceability and scope control
- II. Testable, Incremental Delivery -> VI. Testing and Validation
- III. Quality and Security by Default -> III. Security and Authorization
- IV. Clear Boundaries and Simplicity -> II. Architecture and Separation of Concerns
- V. Transparent Operations -> VII. API and Error Handling
Added principles:
- IV. Business Rule Integrity
- V. Concurrency and Data Integrity
- VIII. Scope Control
Modified sections: Additional Constraints; Development Workflow; Governance
Removed sections: none
Follow-up deferred items: none
-->

# ChangeFlow Constitution

## Core Principles

### I. Specification Before Implementation

Every feature MUST begin with an approved specification that defines user value,
behavior, scope, constraints, and measurable acceptance criteria. Plans and tasks
MUST trace each change to an approved requirement. Implementation MUST NOT
introduce behavior that is absent from the approved specification or recorded as
an explicit approved amendment.

Compliance is met when every plan item and task references an approved
requirement, and review finds no implemented behavior without such a reference.
This prevents scope drift and makes acceptance objectively verifiable.

### II. Architecture and Separation of Concerns

Business logic MUST reside in the Domain or Application layer. Controllers,
routes, and HTTP handlers MUST be limited to transport concerns: request parsing,
structural input validation, authentication context, response mapping, and HTTP
status codes. Business rules MUST NOT be implemented directly in controllers,
routes, or HTTP handlers.

Persistence concerns MUST be separated from business rules. Persistence code MUST
NOT decide business outcomes or state-transition rules. Unnecessary abstractions,
layers, and design patterns MUST NOT be introduced. A new abstraction MUST have an
approved consumer and a documented boundary or testability need.

Compliance is met when review can identify the Domain or Application component
that owns each business decision and the transport and persistence boundaries
around it. Any business decision in a transport or persistence component fails
review. This separation keeps policy testable and replaces the minimum amount of
code when behavior changes.

### III. Security and Authorization

Every protected operation MUST authenticate the caller and authorize the
requested action. Authentication and authorization MUST be enforced server-side.
Client-provided user IDs or roles MUST NOT be trusted as proof of identity or
permission. Access MUST be denied by default.

A requester MUST NEVER approve their own change request, even when that user also
has the Reviewer role. Compliance is met when every protected operation has an
explicit authorization rule and tests cover unauthenticated access, unauthorized
access, and self-approval by a user with both Requester and Reviewer roles. This
prevents client-side bypasses and conflicts of interest.

### IV. Business Rule Integrity

All change-request state transitions MUST follow explicitly defined business
rules. Each rule MUST identify the permitted action, current state, authorized
actor, and resulting state. Invalid or unspecified transitions MUST be rejected.
Approved requests MUST be immutable.

State transitions MUST be atomic and MUST NOT leave partially updated records.
Resubmission after `ChangesRequested` MUST preserve the request's history where
applicable. Compliance is met when an approved transition matrix or equivalent
rule inventory exists, every allowed and denied transition is covered by tests,
state changes are verified through persistence, and a failure test demonstrates
that no partial update remains. These controls make workflow outcomes auditable
and repeatable.

### V. Concurrency and Data Integrity

Concurrent modifications MUST NOT silently overwrite newer data. All mutable
change requests MUST support optimistic concurrency control. Every update and
state transition MUST verify the expected version before committing. A stale
version MUST produce a concurrency conflict and MUST NOT update the record.

Database transactions and constraints MUST be used where necessary to preserve
consistency. Compliance is met when mutable records expose a concurrency token,
conflict tests start competing operations from the same expected version, exactly
one conflicting write succeeds, and persisted data reflects no lost update. These
controls prevent silent data loss in multi-user workflows.

### VI. Testing and Validation

Every business rule and authorization rule MUST have automated test coverage.
Self-approval prevention MUST have an explicit negative test, including a user
with both Requester and Reviewer roles. Tests for critical operations MUST verify
persisted state, not only HTTP responses. Concurrency conflicts MUST be tested.

New or changed behavior MUST have a failing automated test before implementation.
Build and test results MUST reflect commands executed in the current environment.
No feature may be declared accepted solely because the build and automated tests
pass; every acceptance criterion MUST also be evaluated and recorded.

Compliance is met when the requirement-to-test mapping is complete, command output
is reviewable, persisted-state and concurrency tests exist for critical
operations, and acceptance evidence covers each criterion. These requirements
prevent tests that pass while violating workflow or data-integrity rules.

### VII. API and Error Handling

HTTP handlers MUST return consistent and meaningful HTTP status codes. Every
request payload MUST be validated. Errors MUST NOT expose internal implementation
details, sensitive information, or credentials.

Authentication failures, authorization failures, and concurrency conflicts MUST
be distinguishable to clients. They MUST NOT be collapsed into the same generic
error response. Compliance is met when automated API tests verify request
validation, status-code mappings, error redaction, and distinct authentication,
authorization, and concurrency responses. Clear error contracts let clients
respond safely without revealing implementation details.

### VIII. Scope Control

Only approved requirements MUST be implemented. AI, RAG, MCP, Multi-Agent
capabilities, frontend development, and unrelated features are explicitly outside
the initial project scope. New requirements MUST pass through the specification
workflow before implementation.

Compliance is met when every task maps to an approved requirement and review finds
no excluded or unrelated functionality. Any proposed addition MUST identify the
approved specification change before work begins. This keeps the initial delivery
focused and prevents hidden scope expansion.

## Additional Constraints

- Repository configuration and project guidance MUST remain sufficient for a new
  contributor to reproduce setup, tests, and validation.
- Secrets, credentials, tokens, and sensitive personal data MUST NOT be committed
  to the repository or exposed in diagnostic output.
- Third-party dependencies MUST be necessary, actively maintained, and reviewed
  before adoption; lockfiles and exact versions MUST be committed when supported.
- Compatibility, performance, accessibility, or regulatory requirements MUST be
  added to the feature specification when applicable and expressed as measurable
  acceptance criteria.
- Generated artifacts MUST NOT be edited manually unless the generating workflow
  explicitly permits it.

## Development Workflow

Work proceeds through the sequence specify, clarify, plan, tasks, and implement.
Implementation MUST NOT begin until the specification and plan pass their review
gates. The plan MUST identify layer ownership for business rules, the authorization
model, the valid state transitions, the concurrency strategy, and the required
test coverage. Each task MUST identify the approved requirement it advances and
the validation that proves completion.

Implementation MUST begin with failing tests for new or changed behavior. Before
acceptance, the team MUST execute the required tests, inspect persisted state for
critical operations, evaluate every acceptance criterion, and record the resulting
evidence. A passing build alone MUST NOT satisfy the acceptance gate.

Any architectural, security, or workflow deviation MUST be recorded with the
affected principle, scope, justification, risk, compensating control, owner, and
expiration or removal condition. The project owner or an explicitly delegated
reviewer MUST approve the deviation before implementation of the affected change.

## Governance

This constitution supersedes conflicting project practices. A documented law,
contract, or safety requirement takes precedence where this constitution conflicts
with it; the conflict and required amendment MUST be recorded.

Amendments MUST describe the changed principle or section, the reason for the
change, affected in-flight work, and any required migration. Every amendment MUST
include a Sync Impact Report that identifies the version change, modified,
added, and removed governance content, and any deferred work. An amendment becomes
effective after approval by the project owner or an explicitly delegated reviewer.
The Sync Impact Report MUST be removed before the amended constitution is
committed.

Constitution versions follow semantic versioning:

- MAJOR increments for incompatible governance changes, principle removals, or
  principle redefinitions.
- MINOR increments for new principles or materially expanded requirements.
- PATCH increments for clarifications and non-semantic corrections.

Every specification, plan, task review, implementation review, and acceptance
decision MUST record either compliance or an approved deviation for each affected
principle. Inconsistent artifacts MUST block acceptance until reconciled.

Any architectural or security deviation MUST be explicitly documented and
justified. A violation MUST be removed, or recorded with the principle, scope,
impact, risk, compensating control, owner, approval, and remediation or expiry
date. Complexity or functionality that cannot be justified against an approved
requirement and these principles MUST be removed.

**Version**: 2.0.0 | **Ratified**: 2026-11-20 | **Last Amended**: 2026-11-20
