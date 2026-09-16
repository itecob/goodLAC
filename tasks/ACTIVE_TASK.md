# ACTIVE TASK — LAC-B003

## Task ID

`LAC-B003`

## Objective

Prove the generic external-consumer/LAC integration contract after the accepted permission plane and generic Gmail/Calendar adapters. The proof must demonstrate that separate application software can declare capabilities and submit governed requests while remaining unable to administer its own authority or bypass exact approvals.

## In scope

- Implement the smallest generic external-consumer integration boundary required by the controlling specification.
- Use the accepted P001-P006 runtime/admin separation, B001 Gmail precedent, and accepted B002 Calendar permission-managed adapter.
- Prove a separate consumer can identify application/skill context, submit capability-governed typed requests, receive deterministic ALLOW / REQUIRE_APPROVAL / DENY outcomes, and consume successful typed results/receipts.
- Prove registration alone grants zero authority and that authority configuration remains owner/admin-only.
- Prove the consumer cannot access the P004 admin socket/API, mutate standing policy/registry, inject authority/approval fields, or revive closed requests.
- Preserve exact approval binding, pre-dispatch policy re-evaluation, deny precedence, idempotency, durable truth, credential isolation, and fail-closed behavior.
- Use synthetic/local fixtures for consequential external-service mutations. Do not require production Gmail/Calendar credentials.
- Run B003-focused tests plus the accepted regression through B002/P006-UAT and prior phases.
- Produce the Phase 4 candidate and hand it to one fresh independent phase-boundary review.


## Inherited P006 deterministic adversarial regression contract

- The accepted **deterministic adversarial** security gate remains mandatory throughout B003 and the Phase 4 candidate; do not substitute cooperative **model** behavior for boundary testing.
- Regression must retain explicit `DENY` cases and **conditional** standing-policy cases alongside allow/approval paths.
- A model refusal is not evidence that controller, sandbox, adapter, or administration boundaries resisted a hostile request; deterministic hostile requests remain the security gate.
- B003-focused work must not weaken or remove the accepted P006 owner-UAT/stress surface while integrating an external consumer.

## Out of scope

- Chief of Staff workflow, memory, prioritization, briefings, meeting preparation, follow-up, or product UI.
- Production external-service credentials or consequential live effects.
- OpenClaw, Omarchy Agent OS, remote administration, web/TUI administration, enterprise RBAC.
- New authority semantics or weakening any LAC invariant.

## Required inputs

- Accepted B002 owner execution evidence at `qualification/evidence/b002_owner_execution.json`.
- `docs/CONTRACTS.md`, `docs/PERMISSION_MANAGEMENT.md`, ADR-007.
- Accepted P004/P005 runtime/admin boundary.
- Accepted B001 Gmail and B002 Calendar generic adapter contracts.

## Required outputs

- Generic external-consumer integration implementation/fixture.
- Deterministic integration and negative-security tests.
- Regression evidence through accepted B002/P006-UAT and prior phases.
- Phase 4 candidate with durable state/prompt for a fresh independent phase-boundary review.

## Acceptance tests

- external consumer can submit a known registered typed request through the runtime path;
- registration alone grants zero authority;
- owner-configured standing policy governs fresh requests deterministically;
- REQUIRE_APPROVAL cannot execute without an owner exact approval;
- runtime consumer cannot mutate registry/policy or reach the admin socket/API;
- consumer-supplied authority/approval/admin material is rejected or ignored as non-authoritative;
- closed denied requests cannot resume after administration;
- pre-dispatch re-evaluation and deny precedence remain effective;
- duplicate/idempotent effects cannot execute twice;
- credentials remain outside consumer/model context and durable public surfaces;
- accepted B002/P006-UAT and prior deterministic regression remain PASS.

## Package required?

Yes.

## Next task on success

Fresh `PHASE_BOUNDARY_INDEPENDENT_REVIEW` for the completed Phase 4 candidate.
