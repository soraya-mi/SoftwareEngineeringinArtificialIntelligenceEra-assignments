# Feature Specification: Change Request Review Workflow

**Feature Branch**: `001-change-request-workflow`

**Created**: 2026-11-22

**Status**: Draft

**Input**: User description: "Build ChangeFlow, an HTTP API for managing change requests with Requester and Reviewer roles, four workflow states, explicit state transitions, self-approval prevention, immutability of approved requests, and protection against concurrent lost updates."

## Clarifications

### Session 2026-11-22

- Q: Who should be allowed to view a change request? → A: Requesters view only their own requests. Reviewers view other users' `PendingReview` requests and requests they previously reviewed.
- Q: May a user who owns a change request and also has the Reviewer role request changes on that same request? → A: The owner cannot approve their own request, but may request changes on it.
- Q: What feedback must be recorded when a Reviewer requests changes, and how should it be retained? → A: Require a nonblank comment; retain it unchanged in request history and show it to the Requester and authorized Reviewers.
- Q: Should a Requester be able to delete their own Draft change request? → A: Do not support Draft deletion in the initial feature; Drafts remain until submitted.
- Q: Must a Requester change at least one content field before resubmitting a `ChangesRequested` request? → A: Require at least one title, description, or reason value to differ from the content most recently reviewed before resubmission.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create, edit, and submit a Draft request (Priority: P1)

A Requester creates a change request, records why the change is needed, refines their own Draft, and submits it for review.

**Why this priority**: Creating and submitting requests is the entry point for the entire workflow. Without this journey, no request can reach a Reviewer.

**Independent Test**: A user with a current Requester role can create a request, edit its content while it is Draft, submit it, and observe it move to `PendingReview`.

**Acceptance Scenarios**:

1. **Given** an authenticated user has a current Requester role, **When** they create a request with a title, description, and reason, **Then** the request is created in `Draft` and its requester ID is the authenticated caller's identity.
2. **Given** a Requester owns a `Draft` request, **When** they edit its title, description, or reason, **Then** the edited content is retained while the request remains `Draft`.
3. **Given** a Requester owns a `Draft` request, **When** they submit it, **Then** it enters `PendingReview`.
4. **Given** another authenticated user does not own a `Draft` request, **When** they try to edit or submit that request, **Then** the operation is denied and the request content and status remain unchanged.
5. **Given** a caller does not have a current Requester role, **When** they try to create a request, **Then** the operation is denied and no request is created.
6. **Given** a request is already `PendingReview`, **When** any user tries to submit it again, **Then** no duplicate request is created, the status remains `PendingReview`, and the invalid request is rejected.
7. **Given** a Requester owns a request, **When** they view it, **Then** they can see its content and current status.
8. **Given** a Requester does not own a request, **When** they try to view it, **Then** access is denied.
9. **Given** a Requester owns a `Draft` request, **When** they try to delete it, **Then** deletion is denied and the request remains unchanged.

---

### User Story 2 - Review a pending request (Priority: P1)

A Reviewer examines a pending request, approves another user's request, or requests changes on a request, including their own. The system still prevents approval of the reviewer's own request.

**Why this priority**: Review decisions are the core business outcome. Allowing an unauthorized or self-approval would make the workflow invalid even if creation works.

**Independent Test**: A user with a current Reviewer role can approve another user's `PendingReview` request, and an owner with both roles can request changes on their own request but cannot approve it.

**Acceptance Scenarios**:

1. **Given** a `PendingReview` request was created by another user and the caller currently has the Reviewer role, **When** the caller views it, **Then** they can see its content and current status.
2. **Given** a `PendingReview` request was created by another user and the caller currently has the Reviewer role, **When** the caller approves it, **Then** it enters `Approved`.
3. **Given** a `PendingReview` request and a caller with a current Reviewer role, **When** the caller requests changes with a nonblank comment, **Then** it enters `ChangesRequested` and the comment is retained unchanged in its history.
4. **Given** a user has both Requester and Reviewer roles and owns a `PendingReview` request, **When** they request changes, **Then** it enters `ChangesRequested`.
5. **Given** a `PendingReview` request and a caller with a current Reviewer role, **When** the caller requests changes without a nonblank comment, **Then** the operation is denied and the request remains `PendingReview`.
6. **Given** a user has both Requester and Reviewer roles and owns a `PendingReview` request, **When** they try to approve it, **Then** the approval is denied and the request remains `PendingReview`.
7. **Given** a caller lacks a current Reviewer role, **When** they try to approve or request changes, **Then** the operation is denied and the request status remains unchanged.
8. **Given** a request is not `PendingReview`, **When** a Reviewer tries to approve it or request changes, **Then** the operation is denied and the request status remains unchanged.
9. **Given** a Reviewer previously reviewed a request that is no longer `PendingReview`, **When** they view it, **Then** they can see the request and its history.

---

### User Story 3 - Revise a request after changes are requested (Priority: P2)

A Requester incorporates review feedback by updating their own `ChangesRequested` request and resubmitting it for another review.

**Why this priority**: Revision closes the review loop and lets requests recover from requested changes without creating a separate request.

**Independent Test**: A Requester can edit and resubmit their own `ChangesRequested` request, and an unauthorized user cannot perform either action.

**Acceptance Scenarios**:

1. **Given** a Requester owns a `ChangesRequested` request, **When** they edit its title, description, or reason, **Then** the updated content is retained and the request remains `ChangesRequested`.
2. **Given** a Requester owns a `ChangesRequested` request and has changed at least one content field since the most recent review, **When** they submit it, **Then** it enters `PendingReview`.
3. **Given** a Requester owns a `ChangesRequested` request with no content changes since the most recent review, **When** they try to resubmit it, **Then** the operation is denied and the request remains `ChangesRequested`.
4. **Given** a caller does not own a `ChangesRequested` request, **When** they try to edit or submit it, **Then** the operation is denied and the request remains unchanged.
5. **Given** an `Approved` request, **When** its Requester tries to edit or resubmit it, **Then** the operation is denied and the approved content and status remain unchanged.

---

### User Story 4 - Protect workflow integrity during concurrent actions (Priority: P2)

Users receive a clear conflict instead of silently overwriting a newer request when two actions are based on the same earlier request state.

**Why this priority**: A review workflow is not trustworthy if concurrent users can lose edits, overwrite a decision, or move a request through an invalid transition.

**Independent Test**: Two operations begin from the same request state, exactly one succeeds, the other is reported as a concurrency conflict, and the final request reflects only the successful operation.

**Acceptance Scenarios**:

1. **Given** two users update the same request from the same known state, **When** both attempts proceed, **Then** at most one succeeds and the other detects a concurrency conflict without overwriting the successful update.
2. **Given** two Reviewers try to decide the same `PendingReview` request from the same known state, **When** both attempts proceed, **Then** at most one state transition succeeds and the other is rejected without changing the resulting state.
3. **Given** a user's Reviewer role is revoked while a request is `PendingReview`, **When** that user tries to approve it, **Then** the operation is denied because authorization is checked when the action occurs.

### Edge Cases

- A caller tries to claim another user's identity or assign a different requester ID during creation; the system must use the authenticated identity and deny the spoofed ownership.
- A stale edit, submit, approve, or request-changes action arrives after another action has already changed the request; the stale action must not overwrite or regress the newer state.
- Two submission attempts race from `Draft` or `ChangesRequested`; no duplicate request or duplicate transition may result.
- A user loses a role after login or while a request is pending; any later protected action must be denied based on current authorization.
- An `Approved` request receives any edit, submission, approval, or request-changes action; every such action must be denied and the approved content must remain unchanged.
- A request already in a state that does not permit the requested action receives that action; the invalid transition must be rejected rather than treated as a no-op success.
- A Reviewer requests changes without a nonblank comment; the request must remain `PendingReview` and no review-history entry may be created.
- A Requester changes no content after a request enters `ChangesRequested`; resubmission must be denied and the request must remain `ChangesRequested`.
- A user with both roles requests changes on their own `PendingReview` request; the transition is allowed, while any attempt by that user to approve the same request remains denied.
- A Requester tries to delete their `Draft`; the operation is denied and the Draft remains available with unchanged content and status.
- A Requester tries to view another user's request, or a Reviewer tries to view a request they have neither reviewed nor received for pending review; access must be denied.
- A blank title, description, or reason is submitted. Required-field and content-validation behavior is unresolved in Q-005.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST establish the caller's authenticated identity and evaluate the caller's roles when each protected operation is attempted. A caller-provided user ID or role declaration MUST NOT be accepted as proof of identity or permission.
- **FR-002**: The system MUST allow a caller with a current Requester role to create a change request in `Draft` status.
- **FR-003**: The system MUST assign the authenticated caller's identity as the new request's requester ID and MUST NOT accept a different requester identity from the caller.
- **FR-004**: The system MUST retain the title, description, and reason supplied for a change request for its lifetime.
- **FR-005**: The system MUST allow the owner of a `Draft` request, acting with a current Requester role, to edit its title, description, or reason.
- **FR-006**: The system MUST deny edits to a `Draft` request by anyone other than its Requester.
- **FR-007**: The system MUST allow the owner of a `Draft` request, acting with a current Requester role, to submit it, resulting in `PendingReview`.
- **FR-008**: The system MUST allow a caller with a current Reviewer role to approve a `PendingReview` request created by another user, resulting in `Approved`.
- **FR-009**: The system MUST never approve a request when the authenticated Reviewer is also its Requester, even when the caller has both roles.
- **FR-010**: The system MUST allow a caller with a current Reviewer role to request changes on a `PendingReview` request, including a request the caller owns, resulting in `ChangesRequested`.
- **FR-011**: The system MUST allow the owner of a `ChangesRequested` request, acting with a current Requester role, to edit its title, description, or reason.
- **FR-012**: The system MUST allow the owner of a `ChangesRequested` request, acting with a current Requester role and satisfying the revision condition in FR-027, to submit it, resulting in `PendingReview`.
- **FR-013**: The system MUST support only the following state transitions, and MUST reject every other requested transition:

  | Current state | Action | Authorized actor | Resulting state |
  |---------------|--------|------------------|-----------------|
  | `Draft` | Submit | Request owner with a current Requester role | `PendingReview` |
  | `PendingReview` | Approve | Another user with a current Reviewer role | `Approved` |
  | `PendingReview` | Request changes | User with a current Reviewer role, including the request owner | `ChangesRequested` |
  | `ChangesRequested` | Submit | Request owner with a current Requester role and content that differs from the most recently reviewed content | `PendingReview` |

- **FR-014**: The character of a request's status MUST change only through an allowed action in FR-013. Directly assigning a status or treating a rejected transition as successful MUST NOT change the request.
- **FR-015**: Once a request is `Approved`, the system MUST reject all attempts to edit its content or change its status. The approved content and status MUST remain immutable.
- **FR-016**: Every state-transition attempt MUST validate the authenticated caller, the caller's current role, the caller's relationship to the request, and the request's current state before any state change becomes effective.
- **FR-017**: The system MUST protect every mutable request from concurrent lost updates. An operation based on an outdated request state MUST fail with a concurrency conflict and MUST NOT overwrite the newer content or status.
- **FR-018**: If a caller's role is revoked, subsequent protected actions that require that role MUST be denied without changing the request.
- **FR-019**: A repeated submission of a request already in `PendingReview` MUST NOT create a second request or repeat the transition. The rejected-attempt response semantics remain unresolved in Q-006.
- **FR-020**: The system MUST retain an auditable history for every accepted state transition, including the request affected, actor, action, prior state, resulting state, and occurrence time.
- **FR-021**: The system MUST preserve prior request content, before-submission review comments, and transition history when a `ChangesRequested` request is edited and resubmitted.
- **FR-022**: The system MUST distinguish authentication failures, authorization failures, invalid workflow actions, and concurrency conflicts in its responses while avoiding disclosure of sensitive implementation or credential information.
- **FR-023**: A Requester MUST be able to view only requests they created. A Reviewer MUST be able to view other users' `PendingReview` requests and requests they previously reviewed, and MUST NOT view other requests outside those categories.
- **FR-024**: The system MUST NOT support deleting a change request in any state, including `Draft`. A Draft remains available until it is submitted.
- **FR-025**: A Request changes action MUST require a nonblank review comment. The system MUST retain the comment unchanged in request history for at least the request's lifetime and MUST show it to the Requester and authorized Reviewers.
- **FR-026**: An accepted state transition MUST take effect completely or not at all. A failed validation, authorization check, or concurrency check MUST NOT leave a partial content, status, or history update.
- **FR-027**: The system MUST allow submission from `ChangesRequested` only when at least one of title, description, or reason differs from the content most recently reviewed. Otherwise, the system MUST reject the submission and retain `ChangesRequested`.

### Key Entities

- **User**: An authenticated actor with a current identity and zero or more roles. Requester and Reviewer are independent roles that may be held at the same time.
- **Change Request**: A request identified by its requester, title, description, reason, and current status, with enough known state to determine whether a competing action is based on outdated information.
- **Transition Record**: An auditable record of an accepted workflow action, including its actor, prior state, resulting state, action, and occurrence time.
- **Review Feedback**: A required, nonblank comment associated with a request-changes decision. It is immutable, belongs to the transition history, and is visible to the Requester and authorized Reviewers.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of valid transitions in FR-013 produce the documented resulting state, and 100% of transitions not listed in FR-013 are rejected without changing state.
- **SC-002**: 0 self-approvals are accepted across successful, unauthorized, concurrent, and dual-role test scenarios.
- **SC-003**: In every competing-update scenario started from the same request state, exactly one update succeeds, the other reports a conflict, and no successful value is silently overwritten.
- **SC-004**: 100% of edit and transition attempts against an `Approved` request are rejected, with the approved content and status unchanged.
- **SC-005**: 100% of created requests use the authenticated caller as requester, and 100% of attempts to spoof requester identity are rejected.
- **SC-006**: 100% of protected actions attempted after the required role is revoked are denied without changing request state.
- **SC-007**: 100% of accepted state transitions have traceable history containing the request, actor, action, prior state, resulting state, and occurrence time.
- **SC-008**: A representative Requester and Reviewer can demonstrate every P1 and P2 user story without relying on behavior that is absent from this specification.
- **SC-009**: 100% of rejected or conflicting actions leave request content, status, and transition history unchanged, with no partial update.
- **SC-010**: 100% of accepted Request changes actions contain a nonblank comment that remains unchanged and is visible to the Requester and authorized Reviewers.
- **SC-011**: 100% of requests to delete any change request are denied, and the targeted request remains available with unchanged content and status.
- **SC-012**: 100% of resubmissions with no content change after review are rejected and leave the request in `ChangesRequested`.

## Assumptions

- Users are already authenticated, and their current roles can be determined whenever an action is attempted.
- This feature manages the change-request lifecycle only. Executing the underlying code or operational change after approval is outside this specification.
- A change request has exactly one current status and belongs to exactly one Requester.
- Editing a request changes only title, description, or reason. Status and requester identity cannot be edited directly.
- A Reviewer may approve eligible requests created by another user and may request changes on eligible requests, including their own, according to the clarified access rule.
- Transition history and required review comments are retained for at least the request's lifetime, as required by the ChangeFlow Constitution and the clarified review-feedback rule.
- The exact rules for blank values, content length, and content normalization remain open in Q-005; no additional validation rule is silently introduced here.

## Open Questions

These decisions require Product Owner approval. Proposed defaults are recorded only to support clarification and are not approved requirements.

- **Q-005 - Content validation**: Are title, description, and reason all mandatory? May they contain only whitespace? Are there maximum lengths or allowed formats?
  - Proposed default: Require all three, reject whitespace-only values, trim surrounding whitespace, and defer maximum lengths until Product Owner approval.
- **Q-006 - Duplicate-action response**: When a submission or review action is repeated after the first action succeeded, should the API return an explicit invalid-transition/conflict response or behave idempotently and return the already-achieved outcome?
  - Proposed default: Return an explicit invalid-transition result while preserving the already-achieved state and creating no duplicate record.
- **Q-008 - Audit visibility**: Who may view transition history and review feedback beyond the Requester and the Reviewers who acted?
  - Proposed default: Limit access to the Requester and authorized Reviewers.
