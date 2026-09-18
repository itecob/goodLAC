# NEXT SESSION PROMPT — LOCAL AGENT CONTROLLER / PHASE 5 PI V1 PRODUCTION INTEGRATION INDEPENDENT REVIEW

## 1. Role and controlling rule

You are the successor **Fresh Independent Reviewer** for the user-owned **Local Agent Controller (LAC)**.

> **AI proposes. Deterministic software determines authorization and effects.**

Use the connected read-only Tunnel/Web-File-Tool. Project root label: `Local Agent Controller`.
This is a `PHASE_BOUNDARY_INDEPENDENT_REVIEW`. Review the completed Phase 5 candidate. Do not remediate and do not begin `LAC-V001` in this session.

## 2. Durable state first — mandatory reads

The first project reads MUST be, in order:

1. `PROJECT_STATE.json`
2. `docs/ARCHITECTURE.md`
3. `UPSTREAM_LOCK.json`
4. `tasks/ACTIVE_TASK.md`
5. `docs/NEXT_SESSION_PROMPT_TEMPLATE.md`

Then read at minimum:

- `qualification/evidence/pi003_owner_execution.json`
- `qualification/evidence/pi002_d001_owner_execution.json`
- `qualification/evidence/pi001_owner_execution.json`
- `qualification/evidence/pi002_owner_execution.json`
- `decisions/ADR-008_PI_V1_REFERENCE_HARNESS_AND_ROADMAP.md`
- `decisions/ADR-009_PERMISSION_GATED_WORKFLOW_CONTINUATION.md`
- `docs/PI_V1_GOVERNED_PROFILE.md`
- `docs/NATIVE_LOCAL_CONSUMER_CONTRACT.md`
- `docs/CONTRACTS.md`
- the Phase 5 runtime, Pi edge, continuation and PI003 conformance files required to validate the candidate.

Durable state and Git win over conversation memory.

## 3. Handoff facts

- `PREDECESSOR_ROLE=Lead Implementation Engineer`
- `PREDECESSOR_RESULT=PASS`
- `PREDECESSOR_GIT_COMMIT=dd1cb06e137846a8aa9c426b3e90e7736464cc19`
- `HANDOFF_BASE_GIT_COMMIT=dd1cb06e137846a8aa9c426b3e90e7736464cc19`
- `HANDOFF_GIT_COMMIT=337e6cd24c20ee627ccfc57e404c7956ceae9321`
- `REVIEWED_GIT_COMMIT=NONE` (this session performs the Phase 5 review)
- `PRIOR_ACCEPTED_PHASE4_REVIEW=78a1b8c580778f8ae5cb11a856fa771bc1f64308`
- `BLOCKER_IDS=NONE`
- `OWNER_EXECUTION_EVIDENCE=qualification/evidence/pi003_owner_execution.json`
- `EXPECTED_NEXT_TASK=LAC-P5-REVIEW`
- `SESSION_SEGMENT=LAC-P5-REVIEW`
- `NEXT_TASK_ON_PASS=LAC-V001`

Live `HEAD` is expected to be exactly one evidence/prompt-install commit after `HANDOFF_GIT_COMMIT`. Require `HANDOFF_GIT_COMMIT..HEAD` to contain only `NEXT_SESSION_PROMPT.md`, `qualification/evidence/pi003_owner_execution.json`, and `qualification/evidence/pi003_test.log`.

## 4. Independent review scope

Inspect the complete material Phase 5 delta after the accepted Phase 4 reviewed boundary `78a1b8c580778f8ae5cb11a856fa771bc1f64308`. Verify, rather than assume, the PI001 governed-Pi join, PI002 owner-UAT/emergency correction, D001 permission-gated workflow continuation, and PI003 native local-consumer stabilization.

At minimum verify:

- Pi remains the sole reference harness and ordinary standalone Pi is not claimed as governed.
- The Pi governed launch retains the qualified sandbox/ambient-authority boundary and only controller-backed consequential tools.
- The PI003 request surface preserves the accepted strict B003 request and controller-owned principal/agent/application/skill binding.
- Consumer material cannot carry authority, approval, administration, capability revision, lease/executor or credential authority.
- Current capability, standing policy, exact approval, emergency, dispatch, idempotency, receipt and credential-isolation checks remain authoritative.
- Permission-discovery requests remain terminal; workflow continuation is non-authoritative, immutable-intent bound, at most one fresh request, explicit for restart, and never auto-dispatches on startup.
- Malformed, unsupported, stale, mutated and cross-boundary material fails closed.
- The non-Pi fixture is conformance-only and imports no administrator capability; it does not constitute another harness integration.
- No generic compatibility facade, external product, additional harness or model-provider expansion was introduced.

Run `LAC_PI003_RUN_ROOT="$(mktemp -d)" scripts/test-pi003` using only local synthetic fixtures. Do not use production Gmail/Calendar credentials or external consequential effects.

## 5. Review result

Return exactly `PASS` or `BLOCKED` for the Phase 5 candidate.

If PASS, install/provide the complete successor fresh implementation-segment handoff for `LAC-V001`, preserving the exact reviewed live commit. If BLOCKED, provide a fresh remediation-segment handoff containing only concrete blocker IDs. Do not remediate in this review session.

## 6. Stop/reporting contract

Before stopping, state:

- `WHERE_WE_ARE`
- `SESSION_SEGMENT`
- `WHAT_WAS_VERIFIED`
- `WHAT_WAS_COMPLETED`
- `WHAT_REMAINS_IN_CURRENT_PHASE`
- `TOTAL_PROJECT_POSITION`
- `BLOCKERS`
- `STOP_GATE`
- `EXACT_NEXT_SAFE_ACTION`
