# ACTIVE TASK — LAC-P4-REVIEW

## Task ID

`LAC-P4-REVIEW`

## Objective

Perform one fresh independent Phase 4 re-review of the corrected candidate after remediation of `P4-B002`. Verify the durable four-dimensional external-consumer request ownership and the complete Phase 4 boundary; do not remediate.

## In scope

- Verify the complete remediation delta from the previously reviewed Phase 4 candidate.
- Verify every B003 request is durably bound to controller-owned principal/agent/application/skill identity before reuse, approval discovery/use, policy, lease, adapter invocation, terminal replay, or status disclosure.
- Verify cross-application/skill request collision, exact-approval borrowing, terminal replay, status access, and restart persistence fail closed.
- Verify legacy B003 requests lacking the new four-dimensional binding are not retroactively claimable.
- Verify correctly bound B003 normal behavior remains unchanged.
- Verify P4-B001 declaration identity mismatch remains fail-closed before policy decision, lease, or adapter invocation.
- Verify the full accepted Phase 4 authority, approval, closure, idempotency, credential-isolation, admin-boundary, and deterministic sandbox regression chain.
- Return exactly `PASS` or `BLOCKED`.

## Out of scope

- Remediation or implementation changes.
- Chief of Staff workflow/business logic.
- Phase 5 OpenClaw implementation.
- New authentication/RBAC architecture or optional refactors.

## Required inputs

- `qualification/evidence/p4_b002_owner_execution.json`
- `qualification/evidence/p4_b002_test_output.txt`
- corrected B003 runtime, focused P4-B002 tests, and documentation;
- predecessor P4-B001 evidence;
- prior B003/B002/P006-UAT/P006 evidence and contracts;
- binding Phase 4 requirements and permanent invariants.

## Required outputs

- Independent review result: exactly `PASS` or `BLOCKED`.
- If `PASS`, a complete fresh successor implementation prompt for Phase 5 `LAC-O001`; do not implement it in the review session.
- If `BLOCKED`, a complete fresh remediation prompt naming only concrete blocker IDs; do not remediate.

## Acceptance tests

- application/skill A cannot reuse a request durably owned by B even when principal/agent and all consumer request material are identical;
- B exact approval cannot qualify or be consumed through A;
- B successful/failed terminal result cannot be replayed or disclosed through A;
- A status cannot inspect B-owned request;
- restart preserves four-dimensional ownership enforcement;
- legacy unbound request cannot be claimed after upgrade;
- correct binding preserves B003 ALLOW / REQUIRE_APPROVAL / DENY / idempotent replay / status behavior;
- P4-B001 declaration mismatch remains pre-authority fail-closed;
- registration alone grants zero authority;
- consumer cannot inject identity/authority/approval/admin/lease/credential material;
- accepted deterministic regression remains PASS.

## Package required?

No.

## Next task on success

Phase 5 `LAC-O001` OpenClaw integration, in a fresh implementation session only after this re-review passes.
