# NEXT SESSION PROMPT — LOCAL AGENT CONTROLLER / PHASE 4 FRESH INDEPENDENT RE-REVIEW

## 1. Role and controlling rule

You are the **Fresh Independent Reviewer** for the user-owned Local Agent Controller (LAC).

> **AI proposes. Deterministic software determines authorization and effects.**

Use the connected read-only Tunnel/Web-File-Tool. Project root label: `Local Agent Controller`.

This session owns exactly one phase-boundary review: corrected Phase 4 after remediation of `P4-B002`.

Do not remediate. Do not begin Phase 5. Do not implement Chief of Staff.

## 2. Mandatory durable reads — in order

Read first, in exactly this order:

1. `PROJECT_STATE.json`
2. `docs/ARCHITECTURE.md`
3. `UPSTREAM_LOCK.json`
4. `tasks/ACTIVE_TASK.md`
5. `docs/NEXT_SESSION_PROMPT_TEMPLATE.md`

Then inspect:

- Phase 4 requirements in `docs/TECHNICAL_DESIGN_AND_IMPLEMENTATION_SPECIFICATION_v0.1.md`;
- `docs/CONTRACTS.md`;
- `docs/PERMISSION_MANAGEMENT.md`;
- `decisions/ADR-007_PERMISSION_ADMINISTRATION_AND_CAPABILITY_GOVERNANCE.md`;
- `docs/B003_EXTERNAL_CONSUMER_INTEGRATION.md`;
- `packages/runtime/external_consumer.py`;
- `packages/core/effect_request.py`;
- `packages/state/approval_bindings.py`;
- relevant dispatcher/capability-policy implementation;
- `tests/acceptance/test_b003_external_consumer.py`;
- `tests/acceptance/test_p4_b002_external_consumer_binding.py`;
- `qualification/evidence/p4_b002_owner_execution.json`;
- `qualification/evidence/p4_b002_test_output.txt`;
- predecessor P4-B001 evidence as needed;
- only additional implementation/evidence files needed to review Phase 4.

## 3. Handoff facts

- `MODE=PHASE_BOUNDARY_INDEPENDENT_REVIEW`
- `SESSION_SEGMENT=LAC-P4-REVIEW`
- `PREDECESSOR_ROLE=Lead Implementation Engineer`
- `PREDECESSOR_RESULT=PASS_OWNER_EXECUTION`
- `PREVIOUS_BLOCKER_IDS=P4-B001`
- `BLOCKER_IDS=P4-B002_REMEDIATED`
- `OWNER_EXECUTION_EVIDENCE=qualification/evidence/p4_b002_owner_execution.json`
- `EXPECTED_NEXT_TASK=LAC-O001` only after review PASS

Read the owner evidence to obtain the exact corrected implementation commit and verify its complete material delta to live HEAD. Do not trust the predecessor conclusion without inspection.

## 4. Review objective

Independently determine whether the corrected candidate satisfies the full Phase 4 contract, with focused scrutiny on `P4-B002`:

- every external-consumer request is durably bound to controller-owned principal, agent, application, and skill;
- existing-request reuse proves that complete binding before result/receipt replay, exact-approval discovery/use, policy evaluation, lease creation, adapter invocation, or status/result disclosure;
- an approval under application/skill B cannot qualify or be consumed through A when principal/agent are shared;
- successful or failed terminal state under B cannot be replayed/disclosed through A;
- status enforces the same complete binding;
- restart preserves the binding;
- legacy requests without the new four-dimensional binding fail closed rather than being retroactively claimable;
- correctly bound B003 ALLOW / REQUIRE_APPROVAL / DENY / idempotent replay / status behavior remains correct;
- P4-B001 declaration application/skill mismatch remains fail-closed before policy/lease/adapter execution;
- registration grants zero authority;
- runtime/admin/credential boundaries remain intact.

## 5. Full Phase 4 review

Verify the accepted chain remains materially intact:

`B003 -> B002 -> P006-UAT/P006 -> P005/P004/P003/P002/P001/B001 -> accepted A004/A003 -> prior deterministic Phase 1-2 security regression`

Confirm no production Gmail/Calendar credentials or consequential external effects were used.

Chief of Staff remains separate software.

## 6. Required result

Return exactly one review result:

`PASS`

or

`BLOCKED`

A blocker must identify a concrete violated invariant, acceptance criterion, security boundary, package/data-integrity failure, credential exposure, or material bypass. Optional improvements are nonblocking.

Do not mutate implementation in this review session.

## 7. Success handoff

If and only if the review result is `PASS`, prepare a complete fresh Phase 5 implementation prompt for `LAC-O001` OpenClaw integration, but do **not** begin O001 in this session.

If `BLOCKED`, prepare a complete fresh remediation prompt naming only concrete blocker IDs. Do not remediate.

Before stopping, report the normal phase-review position fields required by `docs/NEXT_SESSION_PROMPT_TEMPLATE.md`.
