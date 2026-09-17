# ACTIVE TASK — LAC-P4-REVIEW

## Task ID

`LAC-P4-REVIEW`

## Objective

Perform one fresh independent Phase 4 re-review of the corrected candidate after remediation of `P4-B001`. The reviewer verifies the corrected controller-owned external-consumer identity binding and the complete Phase 4 boundary; it does not remediate.

## In scope

- Verify the corrected implementation commit and its complete material delta from the previously blocked B003 candidate.
- Verify controller-owned principal/agent/application/skill identity binding at the external-consumer boundary.
- Verify declaration `application_id`/`skill_id` are claims checked against the trusted controller binding before policy, lease, or adapter execution.
- Verify the focused P4-B001 tests and the full B003 -> accepted B002 -> P006-UAT/P006 -> prior deterministic regression evidence.
- Verify deterministic adversarial security evidence demonstrates actual controller behavior, including DENY and conditional-policy enforcement; model refusal is not a security pass.
- Verify all existing Phase 4 authority, approval, closure, idempotency, credential-isolation, and admin-boundary invariants remain intact.
- Return exactly `PASS` or `BLOCKED`.

## Out of scope

- Remediation or implementation changes.
- Chief of Staff workflow/business logic.
- OpenClaw, Omarchy Agent OS, or later-phase implementation.
- New authentication/RBAC architecture or optional refactors.

## Required inputs

- `qualification/evidence/p4_b001_owner_execution.json`
- `qualification/evidence/p4_b001_test_output.txt`
- corrected B003 runtime, tests, and documentation;
- prior B003/B002/P006-UAT/P006 evidence and contracts;
- binding Phase 4 requirements and permanent invariants.

## Required outputs

- Independent review result: exactly `PASS` or `BLOCKED`.
- If `PASS`, a complete fresh successor implementation prompt for Phase 5 `LAC-O001`; do not implement it in the review session.
- If `BLOCKED`, a complete fresh remediation prompt naming only concrete blocker IDs; do not remediate in the review session.

## Acceptance tests

- consumer bound to application/skill A cannot borrow B authority by presenting B's valid registered declaration;
- application/skill-scoped ALLOW/default for B cannot authorize consumer A;
- declaration identity mismatch fails before policy decision, lease, or adapter invocation;
- correct declaration + correct trusted binding follows the normal B003 policy path;
- consumer request cannot supply/override controller-owned identity/authority/approval/admin/lease/credential material;
- registration alone grants zero authority;
- unconfigured valid requests terminally deny and create bounded configuration work;
- exact approvals remain owner-created, exact, one-use, expiry-bound, and immediately re-evaluated;
- duplicate successful requests cannot execute twice;
- terminally closed effects cannot revive;
- credentials remain outside consumer/model/public durable surfaces;
- accepted deterministic regression remains PASS.

## Package required?

No.

## Next task on success

Phase 5 `LAC-O001` OpenClaw integration, in a fresh implementation session only after this Phase 4 re-review passes.
