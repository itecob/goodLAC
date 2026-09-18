# NEXT SESSION PROMPT — LOCAL AGENT CONTROLLER / LAC-PI002-D001 PERMISSION-GATED WORKFLOW CONTINUATION

## 1. Role and controlling rule

You are the successor **Lead Implementation Engineer** for the user-owned Local Agent Controller.

> **AI proposes. Deterministic software determines authorization and effects.**

Use the connected read-only Tunnel/Web-File-Tool. Do not redesign or broaden the product.
Do not begin LAC-PI003 in this session.

## 2. Mandatory first reads

Read, in order:

1. `PROJECT_STATE.json`
2. `docs/ARCHITECTURE.md`
3. `UPSTREAM_LOCK.json`
4. `tasks/ACTIVE_TASK.md`
5. `docs/NEXT_SESSION_PROMPT_TEMPLATE.md`

Then read:

- `qualification/evidence/pi002_owner_execution.json`
- `decisions/ADR-009_PERMISSION_GATED_WORKFLOW_CONTINUATION.md`
- `docs/PI_V1_GOVERNED_PROFILE.md`
- only implementation/test files needed for `LAC-PI002-D001`.

## 3. Handoff facts

- `PREDECESSOR_ROLE=Owner UAT Coordinator / Lead Implementation Engineer`
- `PREDECESSOR_RESULT=PASS`
- `PREDECESSOR_GIT_COMMIT=46bd54e8cbc815fadf7a169d98d91f15e78f9a11`
- `HANDOFF_BASE_GIT_COMMIT=fbbaddd1b9cf5e5f1d8c0d81a3350309848f4583`
- `REVIEWED_GIT_COMMIT=78a1b8c580778f8ae5cb11a856fa771bc1f64308`
- `BLOCKER_IDS=NONE`
- `OWNER_EXECUTION_EVIDENCE=qualification/evidence/pi002_owner_execution.json`
- `EXPECTED_NEXT_TASK=LAC-PI002-D001`
- `SESSION_SEGMENT=LAC-PI002-D001`
- `PRIOR_PHASE_REVIEW_REMAINS_ACCEPTED=true`
- `PI002_TESTED_HEAD=fbbaddd1b9cf5e5f1d8c0d81a3350309848f4583`

Verify the complete delta from `fbbaddd1...` through live HEAD. It should consist only of
PI002 evidence plus the owner-approved forward Phase 5 ADR/architecture/task/handoff control
changes. Do not repeat the accepted Phase 4 review merely because HEAD advanced through this
forward roadmap amendment.

## 4. Binding task

Implement `tasks/ACTIVE_TASK.md` exactly.

The core security rule MUST remain:

- the original unconfigured request is terminally denied and can never revive.

The usability correction is above that boundary:

- the governed Pi host suspends the workflow before the model can continue after
  `permission_configuration.required`;
- owner permission configuration remains admin-only;
- after resolution, exactly one fresh canonical request may be created from immutable captured
  intent;
- the fresh request has new identity and undergoes complete current authority evaluation;
- mutation is a new proposal;
- restart preserves recoverability but never auto-dispatches;
- continuation state is non-authoritative and credential-free.

Do not weaken INV-016, INV-017, INV-018, INV-019 or the accepted P002/P003/P004/P005/P006
security contracts. ADR-009 and INV-020 are additive Phase 5 requirements.

## 5. Required validation

Create deterministic coverage for at least:

- configuration-required workflow suspension before model continuation;
- owner ALLOW -> one fresh request -> success;
- owner ASK/REQUIRE_APPROVAL -> fresh request -> exact approval path;
- owner DENY/dismiss/no-change -> no effect and explicit non-authorizing outcome;
- original request remains terminal throughout;
- fresh request identity differs from original;
- security-relevant mutation invalidates continuation;
- duplicate resume/continuation budget is one;
- restart recovery requires explicit resume and does not auto-dispatch;
- stale/expired/malformed continuation fails closed;
- equivalent pending-permission aggregation cannot cross-bind distinct continuations;
- no admin socket/credential/host-fs/process/network/direct-effect bypass;
- retained `scripts/test-pi001` and relevant Phase 4 gates PASS.

Use local synthetic fixtures only. No production credentials or external consequential effects.

## 6. Package/stop rule

Complete D001 in this fresh session, validate it, and deliver one owner-executable package.
On successful owner execution, advance to `LAC-PI003` and install the corresponding successor
prompt. Stop at `OWNER_EXECUTION_REQUIRED`; do not implement PI003 in this conversation.

Before stopping report:

- `WHERE_WE_ARE`
- `SESSION_SEGMENT`
- `WHAT_WAS_VERIFIED`
- `WHAT_WAS_COMPLETED`
- `WHAT_REMAINS_IN_CURRENT_PHASE`
- `TOTAL_PROJECT_POSITION`
- `BLOCKERS`
- `STOP_GATE`
- `EXACT_NEXT_SAFE_ACTION`
