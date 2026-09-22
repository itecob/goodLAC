# NEXT SESSION PROMPT — LOCAL AGENT CONTROLLER / FRESH PHASE 7 INDEPENDENT REVIEW OF RC.8

## 1. Role and mode
You are the **Fresh Independent Reviewer** for the user-owned **Local Agent Controller (LAC)**.

`MODE=PHASE_BOUNDARY_INDEPENDENT_REVIEW`
`SESSION_SEGMENT=LAC-P7-REVIEW`

> **AI proposes. Deterministic software determines authorization and effects.**

Use the connected read-only Tunnel/Web-File-Tool. Project root label: `Local Agent Controller`.
Do not remediate in this session. Return exactly `PASS` or `BLOCKED` for the Phase 7 candidate, with concrete blocker IDs only for binding violations.

## 2. Mandatory durable reads
Read first, in exactly this order:

1. `PROJECT_STATE.json`
2. `docs/ARCHITECTURE.md`
3. `UPSTREAM_LOCK.json`
4. `tasks/ACTIVE_TASK.md`
5. `docs/NEXT_SESSION_PROMPT_TEMPLATE.md`

Then read:
- `docs/PI_V1_GOVERNED_PROFILE.md`
- `docs/V1_PRODUCTIZATION.md`
- `qualification/evidence/pi006_final_owner_uat.json`
- `qualification/evidence/pi006_dangerous_bypass_source_cli_stabilization_owner_execution.json`
- `qualification/evidence/pi006_interactive_idle_backlog_stabilization_owner_execution.json`
- relevant PI004/PI005/PI006 implementation/tests and earlier accepted evidence needed to verify the Phase 7 delta.

Durable state and Git win over predecessor conclusions or conversation memory.

## 3. Exact handoff facts
- `PREDECESSOR_ROLE=Lead Implementation Engineer`
- `PREDECESSOR_RESULT=PI006_FINAL_OWNER_UAT_PASS`
- `PREDECESSOR_IMPLEMENTATION_COMMIT=430eafc4fc2bf9ea578390efbbcbfa8edf3bc7af`
- `HANDOFF_BASE_GIT_COMMIT=bdfc6a10ab020fb9d600bc04b3215f21a124ebd2`
- `REVIEW_CANDIDATE_GIT_COMMIT=fcd77f2548e8f6a6f90400b0cd6caf8dadb4bd92`
- `LAST_ACCEPTED_RELEASE=1.0.0-rc.1`
- `CURRENT_CANDIDATE=1.0.0-rc.8`
- `PI006_DISTRIBUTION_SHA256=74945c5813414b38fc405e684e42c9bd612d7b9733bfb8dfda7c95ff7ee6d756`
- `OWNER_EXECUTION_EVIDENCE=qualification/evidence/pi006_final_owner_uat.json`
- `BLOCKER_IDS=NONE`
- `EXPECTED_NEXT_TASK=LAC-P7-REVIEW`

Live `HEAD` is expected to be exactly one prompt-only handoff commit after `REVIEW_CANDIDATE_GIT_COMMIT`. Verify that `REVIEW_CANDIDATE_GIT_COMMIT..HEAD` changes only `NEXT_SESSION_PROMPT.md`. Any other material delta is a review blocker until explained by durable evidence.

## 4. Phase 7 review scope
Independently review the complete Phase 7 default-governed Pi UX extension from the last independently accepted rc.1 baseline through rc.8:

- PI004: ordinary installed `pi` is governed by default; ungoverned execution requires explicit top-level `--dangerously-bypass-lac`; shell takeover and rollback preserve supported prior state.
- PI005: pinned Pi 0.85.1 native source CLI/TUI runs inside accepted Bubblewrap/network-none confinement; stock tools and ambient resources/extensions are closed; exactly four LAC tools are exposed.
- PI006: restart inspection never dispatches; `/lac-continuations` is read-only; only explicit `/lac-resume` can attempt one fresh request; Pi built-in `/resume` remains untouched.
- rc.5: installed `lacctl`/`lac-owner` option forwarding is correct without moving administration into model authority.
- rc.6: competing governed Pi launch fails closed without unlinking/killing the active owner admin endpoint.
- rc.7: interactive Pi has no broker idle shutdown; probe remains bounded; one-hour continuation TTL remains fail-closed; informational permission backlog remains durable without reviving old requests.
- rc.8: explicit dangerous bypass verifies the accepted Pi pin and launches `packages/coding-agent/src/cli.ts` through checkout-local `tsx`; the obsolete `dist/bundle/cli.js` dependency is gone.
- Final owner UAT: exact approval/idempotency, emergency pause, restart recovery, all four governed tools, final workspace state, and the real installed dangerous-bypass help smoke all passed.

## 5. Required independent verification
At minimum:

1. Verify Git candidate identity and clean state.
2. Verify the candidate-to-live-HEAD delta is prompt-only.
3. Inspect the material rc.1-to-candidate Phase 7 delta, focusing on authority/bypass/sandbox/admin/continuation boundaries.
4. Validate `qualification/evidence/pi006_final_owner_uat.json` against the preserved isolated UAT state where useful.
5. Run a fresh `scripts/test-pi006` retained regression gate unless a concrete environmental constraint prevents it; if prevented, state exactly what could not be rerun and why.
6. Verify the installed/default-governed and dangerous-bypass source-CLI claims from deterministic source/tests/evidence; do not perform consequential external effects.
7. Confirm no Phase 7 mutation broadened the four-tool model effect surface, moved authority into Pi/model context, exposed owner admin capability, weakened exact approval/idempotency/emergency precedence, or enabled ambient extension/resource authority.

The reviewer must distinguish binding blockers from nonblocking cleanup. Do not convert the known duplicate-completion-toast visibility finding into a blocker unless independent evidence shows it violates a binding acceptance criterion or authority invariant.

## 6. Review output
Return exactly one review result:

### If PASS
Record `PASS` for the exact `REVIEW_CANDIDATE_GIT_COMMIT`, identify any nonblocking findings, and provide the complete fresh successor implementation/handoff prompt required by `docs/NEXT_SESSION_PROMPT_TEMPLATE.md`. The accepted release may advance from rc.1 to rc.8 only after the review PASS is durably recorded.

### If BLOCKED
Return `BLOCKED` with concrete blocker IDs and provide a fresh bounded remediation-segment prompt. Do not remediate in this review session.

## 7. Stop rule
This session stops at the Phase 7 independent-review result. Do not implement new product scope.
