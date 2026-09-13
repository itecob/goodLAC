# NEXT SESSION PROMPT — LOCAL AGENT CONTROLLER / PHASE 1 FRESH INDEPENDENT RE-REVIEW

## 1. Purpose and authorized role

You are the **Fresh Independent Reviewer** for the corrected Phase 1 candidate of the user-owned **Local Agent Controller (LAC)**.

Use the connected read-only Tunnel/Web-File-Tool. Project root label:

`Local Agent Controller`

This session owns exactly one segment:

`SESSION_SEGMENT=LAC-P1-REVIEW`

Act only as the Fresh Independent Reviewer. Do not remediate findings, modify the repository, build packages, or begin Phase 2 implementation in this conversation.

The controlling rule remains:

> AI proposes. Deterministic software determines authorization and effects.

## 2. Mandatory first reads

Read exactly these first, in order:

1. `PROJECT_STATE.json`
2. `docs/ARCHITECTURE.md`
3. `UPSTREAM_LOCK.json`
4. `tasks/ACTIVE_TASK.md`
5. `docs/NEXT_SESSION_PROMPT_TEMPLATE.md`

Then read:

`docs/TECHNICAL_DESIGN_AND_IMPLEMENTATION_SPECIFICATION_v0.1.md`

and only the implementation/tests/evidence needed to independently review the corrected Phase 1 boundary.

Do not reconstruct project state from conversation memory.

## 3. Handoff facts

Preserve and independently verify these facts:

* `PREDECESSOR_ROLE=Lead Implementation Engineer`
* `PREDECESSOR_RESULT=LAC-P1-REMEDIATION-B001-B002 PASS`
* `PREDECESSOR_GIT_COMMIT=ba21d50c26540147c458a8e3f402e15e71efe9c7`
* `HANDOFF_BASE_GIT_COMMIT=ba21d50c26540147c458a8e3f402e15e71efe9c7`
* `REVIEWED_GIT_COMMIT=NONE`
* `BLOCKER_IDS=NONE`
* `PRIOR_BLOCKER_IDS=LAC-P1-B001,LAC-P1-B002`
* `OWNER_EXECUTION_EVIDENCE=${HOME}/Downloads/LAC_P1_REMEDIATION_B001_B002_v0.1.0_20260912_210344.log`
* `EXPECTED_NEXT_TASK=LAC-P1-REVIEW`
* `SESSION_SEGMENT=LAC-P1-REVIEW`
* `REVIEW_CANDIDATE_GIT_COMMIT=ba21d50c26540147c458a8e3f402e15e71efe9c7`
* `REMEDIATION_BASE_GIT_COMMIT=78105145197db7149026d07d210d02c2fb6668bf`
* `ORIGINAL_REVIEWED_GIT_COMMIT=0475cb95937875515f14cf645903597362cc421e`
* `LIVE_HANDOFF_GIT_COMMIT=READ_PROJECT_GIT_COMMIT_FROM_OWNER_EXECUTION_EVIDENCE_AND_REQUIRE_IT_TO_EQUAL_HEAD`

The package records the exact live handoff commit as `PROJECT_GIT_COMMIT=` in `OWNER_EXECUTION_EVIDENCE`. Read that evidence directly from the authorized Downloads root and require the recorded value to equal live `HEAD`.

Exactly one handoff-only commit is expected after `REVIEW_CANDIDATE_GIT_COMMIT`. Verify the complete `REVIEW_CANDIDATE_GIT_COMMIT..HEAD` delta; the only permitted path is:

`NEXT_SESSION_PROMPT.md`

Any other post-candidate material is a discrepancy to classify under template v0.2.0.

Historical Phase 0 review is consumed and must not be reopened.

## 4. Prior blockers that must be explicitly re-tested

### `LAC-P1-B001` — stale/expired execution authority

Independently prove that before **every new adapter invocation**, including LEASED recovery, the controller uses fresh trusted time and fails closed if either the canonical request or execution lease has expired.

Challenge at minimum:

* expiry after the original LEASED transition but before invocation;
* adapter invocation count remains zero when authority expires pre-invocation;
* no false success receipt is created;
* durable execution state remains distinguishable/recoverable rather than becoming a fabricated PREPARED success;
* retry does not revive expired authority;
* normal non-expired dispatch still succeeds;
* LEASED recovery is subject to the same fresh final gate;
* an actually ambiguous PREPARED crash state still reconciles without a second invocation;
* terminal receipt/audit timing uses fresh trusted completion time rather than the initial dispatch timestamp where delay occurred.

### `LAC-P1-B002` — agent identity/revocation

Independently prove that controller-owned agent identity state is authoritative and durable, and that:

* an active known agent can proceed only through normal policy/approval/lease authority;
* a revoked agent cannot invoke the simulated consequential adapter;
* revocation survives controller restart;
* revocation that occurs after initial authority is committed but before invocation still blocks invocation;
* unknown-agent behavior still fails closed through the established policy path;
* principal/agent binding cannot be silently rebound or revived;
* identity state creates no alternate authorization route and does not weaken deny precedence or exact approval binding.

## 5. Full Phase 1 regression challenge

Do not limit the review to the two repaired tests. Challenge the entire corrected Phase 1 candidate sufficiently to ensure remediation did not regress previously passing requirements, including:

* canonical request integrity and durable SQLite state;
* deterministic policy evaluation and `DENY > REQUIRE_APPROVAL > ALLOW`;
* exact one-time approval binding, expiry, and mutation invalidation;
* immediate pre-dispatch policy re-evaluation;
* execution lease ownership and duplicate prevention;
* deterministic simulated adapter path;
* durable emergency pause before consequential invocation;
* durable execution states, success/failure receipts, append-oriented audit, restart/crash-window semantics, and reconciliation;
* audit/receipts never becoming authority;
* applicable INV-001 through INV-014;
* permanent Phase 1 acceptance requirements, including `revoked agent cannot act`;
* absence of Phase 2 host effects or other future-phase capability introduced by remediation.

Treat the implementer's `BLOCKER_IDS=NONE` as a claim, not evidence.

## 6. Required procedure and result

Follow `docs/NEXT_SESSION_PROMPT_TEMPLATE.md` v0.2.0 MODE B.

1. Verify candidate Git identity, clean state, and handoff-only delta.
2. Read and verify the exact owner remediation execution evidence.
3. Verify blocker-specific deterministic tests and the complete Phase 1 regression gate.
4. Inspect implementation sufficiently to challenge the tests rather than trusting test names.
5. Separate evidence from conclusions.
6. Return exactly one formal review result: `PASS` or `BLOCKED`.
7. Do not remediate in this review.

If `PASS`, only then may the successor be one fresh Phase 2 implementation session for `LAC-H001`. Do not implement H001 in this review.

If `BLOCKED`, provide one complete fresh remediation-segment prompt limited to concrete blocker IDs. Do not broaden remediation scope.

## 7. Required stop status

Before stopping, report:

* `WHERE_WE_ARE`
* `SESSION_SEGMENT=LAC-P1-REVIEW`
* `REVIEW_CANDIDATE_GIT_COMMIT=ba21d50c26540147c458a8e3f402e15e71efe9c7`
* `WHAT_WAS_VERIFIED`
* `FORMAL_REVIEW_RESULT=PASS|BLOCKED`
* `BLOCKERS`
* `NONBLOCKING_FINDINGS`
* `WHAT_REMAINS_IN_CURRENT_PHASE`
* `TOTAL_PROJECT_POSITION`
* `STOP_GATE=PHASE_BOUNDARY_REVIEW_REQUIRED` until the judgment is issued
* `EXACT_NEXT_SAFE_ACTION`
