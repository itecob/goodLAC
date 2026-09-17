# ACTIVE TASK — LAC-P4-REVIEW

## Task ID

`LAC-P4-REVIEW`

## Objective

Perform one fresh independent phase-boundary review of the completed Phase 4 permission-managed external-effects candidate through LAC-B003. The reviewer verifies the candidate; it does not remediate it.

## In scope

- Verify candidate Git identity and the complete material delta for Phase 4 completion through B003.
- Verify the binding Phase 4 permission-management requirements and LAC invariants remain satisfied.
- Inspect deterministic qualification evidence, including B003 focused tests and accepted B002/P006-UAT/P006 regression.
- Verify the B003 generic external-consumer contract keeps authority, policy, approvals, credentials, leases, receipts, and administration controller-owned.
- Return exactly `PASS` or `BLOCKED` with concrete blocker IDs only for binding failures.

## Out of scope

- Remediation or implementation changes.
- Chief of Staff workflow/business logic.
- OpenClaw, Omarchy Agent OS, or later-phase implementation.
- New scope or optional refactors.

## Required inputs

- `qualification/evidence/b003_owner_execution.json`
- `qualification/evidence/b003_test_output.txt`
- B003 implementation and tests.
- Phase 4 P001-P006/P006-UAT/B002 evidence and contracts.
- Binding specification Phase 4 acceptance requirements and permanent invariants.

## Required outputs

- Independent review result: exactly `PASS` or `BLOCKED`.
- If `PASS`, a complete fresh successor implementation prompt for the next LAC task from the controlling specification; do not implement it in the review session.
- If `BLOCKED`, a complete fresh remediation prompt naming only concrete blocker IDs; do not remediate in the review session.

## Acceptance tests

- candidate Git/state/task/prompt/evidence are mutually consistent;
- registration grants zero authority;
- unknown/unconfigured requests fail closed and terminal requests do not revive;
- standing policy, conditional rules, deny precedence and exact approval semantics remain deterministic;
- runtime consumers cannot administer registry/policy or reach the owner admin surface;
- external consumer cannot inject identity/authority/approval/admin material;
- pre-dispatch policy re-evaluation remains effective;
- duplicate/idempotent effects cannot execute twice;
- credentials remain outside consumer/model/public durable surfaces;
- B002/P006-UAT/P006 and prior deterministic regression remain accepted/pass;
- B003 contains no Chief of Staff business logic and uses no production external effects.

## Package required?

No.

## Next task on success

Resolve the next LAC implementation segment from the controlling specification after Phase 4 acceptance. The current specification identifies Phase 5 `LAC-O001` OpenClaw integration; Chief of Staff is separate software and is not implemented in this repository.
