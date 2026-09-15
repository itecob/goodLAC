# NEXT SESSION PROMPT — LOCAL AGENT CONTROLLER / P002 UNKNOWN-REQUEST QUARANTINE

`SESSION_SEGMENT=LAC-P002`
`MODE=IMPLEMENTATION_SEGMENT`

Use the connected Web-File-Tool. Treat durable repository state and Git history as authority. This session owns **only** `LAC-P002` unknown-request quarantine and bounded pending-permission queue implementation. Do not begin P003, P004, `lacctl`, Calendar, generic consumer B003, or Chief of Staff implementation in this session.

## Mandatory first reads — exact order

1. `PROJECT_STATE.json`
2. `docs/ARCHITECTURE.md`
3. `UPSTREAM_LOCK.json`
4. `tasks/ACTIVE_TASK.md`
5. `docs/NEXT_SESSION_PROMPT_TEMPLATE.md`

Then read:

- `docs/PERMISSION_MANAGEMENT.md`;
- `decisions/ADR-007_PERMISSION_ADMINISTRATION_AND_CAPABILITY_GOVERNANCE.md`;
- `docs/CONTRACTS.md` capability/permission sections;
- `docs/CAPABILITY_MANIFEST_v1.md`;
- `qualification/evidence/p001_owner_execution.json`;
- P001 `packages/capabilities/` and its focused tests;
- only the effect-request/policy/dispatcher/state interfaces and tests needed for P002.

## Handoff facts to verify; do not assume

- `PREDECESSOR_ROLE=Lead Implementation Engineer`
- `PREDECESSOR_RESULT=OWNER_EXECUTION_PASS`
- `PREDECESSOR_GIT_COMMIT=a32612326604d869326f4ef475eb06c29cca8261`
- `HANDOFF_BASE_GIT_COMMIT=31c66e26ad1eab06065c3f38b2c22620db8e402a`
- `OWNER_EXECUTION_EVIDENCE=qualification/evidence/p001_owner_execution.json`
- `BLOCKER_IDS=NONE`
- `EXPECTED_PHASE=PHASE_4_PERMISSION_MANAGEMENT`
- `EXPECTED_ACTIVE_TASK=LAC-P002`
- `EXPECTED_NEXT_TASK=LAC-P003`

B001 Gmail remains accepted as a generic effect-adapter precursor. P001 registration remains descriptive and grants zero authority. The prior `LAC_B002_CALENDAR_ADAPTER_v0.1.0` package remains superseded and must not be executed. Chief of Staff remains separate software.

## Required lifecycle

1. Perform bounded predecessor verification. Confirm P001 owner evidence is valid, the P001 implementation commit is in Git history, durable state/task/prompt are mutually consistent, P001 focused tests/regression evidence passed, and the live HEAD delta after the P001 implementation commit is handoff-only.
2. Implement `LAC-P002` completely as defined by `tasks/ACTIVE_TASK.md` and the binding permission-management design.
3. Preserve all LAC invariants plus: registration grants no authority; unknown/new capability/resource/material argument shape is terminal `DENY`; pending permission is informational/admin work rather than a resumable effect; runtime consumers cannot administer registry/policy/pending resolution; later changes never revive a closed effect.
4. Use deterministic local/synthetic fixtures. Do not use production credentials or external consequential effects.
5. Run focused P002 tests and the applicable accepted regression gate including P001 and B001; correct in-scope defects before handoff.
6. Produce one owner-executable package that completes P002 and activates fresh `LAC-P003` on success. Stop at `OWNER_EXECUTION_REQUIRED`; do not implement P003 in this conversation.

## Scope discipline

Do not add the scoped conditional standing-policy evaluator, external admin socket/API, `lacctl`, permission-management E2E, Calendar, Chief of Staff E2E, OpenClaw, Omarchy Agent OS, web UI/TUI, or enterprise RBAC in P002.

## Required final status fields

- `WHERE_WE_ARE=`
- `SESSION_SEGMENT=LAC-P002`
- `PREDECESSOR_RESULT=OWNER_EXECUTION_PASS`
- `WHAT_WAS_VERIFIED=`
- `WHAT_WAS_COMPLETED=`
- `WHAT_REMAINS_IN_CURRENT_PHASE=`
- `TOTAL_PROJECT_POSITION=`
- `BLOCKERS=`
- `STOP_GATE=`
- `EXACT_NEXT_SAFE_ACTION=`
