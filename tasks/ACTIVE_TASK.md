# ACTIVE TASK — LAC-P6-REVIEW

## Task ID
`LAC-P6-REVIEW`

## Objective
Independently determine whether the exact LAC-V001 Phase 6 productization candidate satisfies the binding v1 productization requirements and preserves the accepted LAC authority/security boundary.

## In scope
- Verify exact candidate Git identity, clean state and V001 owner-execution evidence.
- Inspect installer/distribution, configuration, governed Pi launcher integration, owner administration UX, upgrade/backup/rollback/recovery and operating documentation.
- Verify clean-install, upgrade, rollback, restart/non-auto-dispatch, permission/approval, duplicate-prevention, receipt, sandbox/admin/credential-isolation and retained regression evidence.
- Run bounded fresh deterministic conformance probes using local synthetic fixtures where needed.
- Return exactly PASS or BLOCKED; do not remediate implementation in the review session.

## Out of scope
- New implementation or remediation.
- Additional harnesses, external products, compatibility facades or model-provider expansion.
- Moving canonical authority into packaging, Pi, a launcher or UI.

## Required inputs
- Exact LAC-V001 implementation commit recorded in `qualification/evidence/v001_owner_execution.json`.
- Exact live candidate commit and owner execution evidence.
- `docs/TECHNICAL_DESIGN_AND_IMPLEMENTATION_SPECIFICATION_v0.1.md` Phase 6/package requirements.
- `docs/V1_PRODUCTIZATION.md`, `docs/PI_V1_GOVERNED_PROFILE.md`, `docs/NATIVE_LOCAL_CONSUMER_CONTRACT.md`, and `docs/CONTRACTS.md`.
- `scripts/test-v001` and retained Phase 5 gates.

## Required outputs
- Fresh independent review result: `PASS` or `BLOCKED`.
- Concrete blocker IDs only for binding violations.
- Durable successor handoff appropriate to the result.

## Acceptance tests
- Productization requirements are materially implemented and reproducible.
- Canonical authority and accepted Phase 5 security semantics remain unchanged.
- Owner package evidence demonstrates exact-preinstall qualification and fail-closed rollback.
- Applicable deterministic gates pass from the reviewed candidate.

## Package required?
`review-dependent`

## Next task on success
Record the independently accepted v1 release candidate and close the active v1 build roadmap; any later roadmap expansion requires an explicit owner decision.
