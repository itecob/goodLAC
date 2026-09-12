# NEXT SESSION PROMPT — LOCAL AGENT CONTROLLER / PHASE 1 FRESH INDEPENDENT BOUNDARY REVIEW

## Purpose

This is the one **fresh independent Phase 1 boundary review** for the user-owned Local Agent Controller.

Use the connected read-only Tunnel/Web-File-Tool. Project root label: `Local Agent Controller`.

This session owns exactly one segment:

`SESSION_SEGMENT=LAC-P1-REVIEW`

Act only as the **Fresh Independent Reviewer**. Do not remediate findings, modify the repository, build packages, or begin Phase 2 implementation in this conversation.

## Mandatory first reads

Read exactly these first, in order:

1. `PROJECT_STATE.json`
2. `docs/ARCHITECTURE.md`
3. `UPSTREAM_LOCK.json`
4. `tasks/ACTIVE_TASK.md`
5. `docs/NEXT_SESSION_PROMPT_TEMPLATE.md`

Then read the controlling specification and only additional files/evidence needed to review Phase 1. Durable state and Git are authoritative.

## Handoff facts

- `PREDECESSOR_ROLE=Lead Implementation Engineer`
- `PREDECESSOR_RESULT=LAC-C010 PASS`
- `PREDECESSOR_GIT_COMMIT=0475cb95937875515f14cf645903597362cc421e`
- `HANDOFF_BASE_GIT_COMMIT=0475cb95937875515f14cf645903597362cc421e`
- `REVIEWED_GIT_COMMIT=NONE`
- `BLOCKER_IDS=NONE`
- `OWNER_EXECUTION_EVIDENCE=${HOME}/Downloads/LAC_P1_C010_RECEIPTS_AUDIT_v0.1.0_20260912_181144.log`
- `EXPECTED_NEXT_TASK=LAC-P1-REVIEW`
- `SESSION_SEGMENT=LAC-P1-REVIEW`
- `REVIEW_CANDIDATE_GIT_COMMIT=0475cb95937875515f14cf645903597362cc421e`

Historical Phase 0 review is already consumed and must not be reopened.

Exactly one handoff commit is expected after `REVIEW_CANDIDATE_GIT_COMMIT`. Verify `REVIEW_CANDIDATE_GIT_COMMIT..HEAD`; the only permitted path is:

- `NEXT_SESSION_PROMPT.md`

If that is the complete delta, preserve the candidate identity across the non-material handoff commit and review `REVIEW_CANDIDATE_GIT_COMMIT`. Any other post-candidate material is a discrepancy to classify under template v0.2.0.

Read the recorded C010 owner execution log directly from the authorized Downloads root. Do not require the owner to paste successful deterministic output again.

## Review objective

Independently determine whether the completed Phase 1 C001-C010 walking skeleton satisfies the binding Phase 1 specification and controller invariants.

Challenge implementation and deterministic evidence rather than trusting predecessor conclusions. In particular verify:

- durable SQLite state and predecessor-to-current migrations;
- canonical typed effect requests and deterministic policy decisions;
- exact one-time approval binding and mutation invalidation;
- immediate pre-dispatch policy re-evaluation and deny precedence;
- execution-lease ordering and duplicate ownership;
- deterministic simulated adapter path;
- durable emergency pause before consequential invocation;
- C010 canonical execution states, success/failure receipts, append-oriented audit, restart/crash-window semantics, and duplicate reconciliation;
- audit/receipts never becoming authorization;
- the required Phase 1 demonstrations and applicable permanent acceptance tests;
- absence of Phase 2 effects or bypass capability introduced early.

A review finding may block only when it concretely violates a binding invariant, acceptance criterion, security boundary, data integrity, effect-duplication rule, required functionality, package/reproducibility requirement, or other blocker class defined by the project. Optional improvements are `NONBLOCKING` and do not prevent PASS.

## Required procedure

Follow template v0.2.0 MODE B.

1. Verify exact candidate Git identity, clean state, and expected handoff-only delta.
2. Verify the C010 owner-execution evidence and deterministic Phase 1 gate.
3. Inspect the implementation and tests needed to independently challenge all Phase 1 acceptance criteria.
4. Separate evidence from conclusions.
5. Return exactly `PASS` or `BLOCKED` as the formal review result.
6. Do not remediate.
7. If `PASS`, provide a complete populated successor prompt for one fresh implementation session whose active segment is `LAC-H001`; do not implement H001 here.
8. If `BLOCKED`, provide a complete populated fresh remediation-segment prompt limited to the concrete blocker IDs; do not remediate here.

## Required stop status

Report `WHERE_WE_ARE`, `SESSION_SEGMENT=LAC-P1-REVIEW`, `REVIEW_CANDIDATE_GIT_COMMIT`, `WHAT_WAS_VERIFIED`, `FORMAL_REVIEW_RESULT`, `BLOCKERS`, `NONBLOCKING_FINDINGS`, `WHAT_REMAINS_IN_CURRENT_PHASE`, `TOTAL_PROJECT_POSITION`, `STOP_GATE`, and `EXACT_NEXT_SAFE_ACTION`.
