# NEXT SESSION PROMPT — LOCAL AGENT CONTROLLER / P003 SCOPED STANDING POLICY

`SESSION_SEGMENT=LAC-P003`
`MODE=IMPLEMENTATION_SEGMENT`

Use the connected Web-File-Tool. Treat durable repository state and Git history as authority. This session owns **only** `LAC-P003` scoped/conditional standing-permission policy implementation. Do not begin P004, P005, P006, Calendar, generic consumer B003, `lacctl`, or Chief of Staff implementation in this session.

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
- `qualification/evidence/p002_owner_execution.json`;
- P001 `packages/capabilities/` registry/manifest implementation;
- P002 quarantine/pending-permission implementation and focused tests;
- only existing policy/dispatcher/state interfaces and tests needed for P003.

## Handoff facts to verify; do not assume

- `PREDECESSOR_ROLE=Lead Implementation Engineer`
- `PREDECESSOR_RESULT=OWNER_EXECUTION_PASS`
- `PREDECESSOR_GIT_COMMIT=f74f4b39e0116cd2d9d8b3bdcf8eaaa3dccb958d`
- `HANDOFF_BASE_GIT_COMMIT=0afe79de78d238ec43a91f7805cc721ca2458001`
- `OWNER_EXECUTION_EVIDENCE=qualification/evidence/p002_owner_execution.json`
- `BLOCKER_IDS=NONE`
- `EXPECTED_PHASE=PHASE_4_PERMISSION_MANAGEMENT`
- `EXPECTED_ACTIVE_TASK=LAC-P003`
- `EXPECTED_NEXT_TASK=LAC-P004`

P001 registration remains descriptive and grants zero authority. P002 unknown/new material is terminal `DENY`; pending permission is informational/admin work and never resumes a closed effect. B001 Gmail remains accepted as a generic effect-adapter precursor. The prior `LAC_B002_CALENDAR_ADAPTER_v0.1.0` package remains superseded and must not be executed. Chief of Staff remains separate software.

## Required lifecycle

1. Perform bounded predecessor verification. Confirm P002 owner evidence is valid, the P002 implementation commit is in Git history, durable state/task/prompt are mutually consistent, P002 focused tests/regression evidence passed, and the live HEAD delta after the P002 implementation commit is handoff-only.
2. Implement `LAC-P003` completely as defined by `tasks/ACTIVE_TASK.md` and the binding permission-management design.
3. Preserve all LAC invariants plus P001 zero-authority registration, P002 terminal quarantine/non-resumability, deterministic trusted-metadata-only conditions, and `DENY > REQUIRE_APPROVAL > ALLOW` equal-specificity precedence.
4. Use deterministic local/synthetic fixtures. Do not use production credentials or external consequential effects.
5. Run focused P003 tests and the applicable accepted regression gate including P001, P002, and B001; correct in-scope defects before handoff.
6. Produce one owner-executable package that completes P003 and activates fresh `LAC-P004` on success. Stop at `OWNER_EXECUTION_REQUIRED`; do not implement P004 in this conversation.

## Scope discipline

Do not add the external admin socket/API, peer-UID boundary, `lacctl`, permission-management E2E, Calendar, Chief of Staff E2E, OpenClaw, Omarchy Agent OS, web UI/TUI, or enterprise RBAC in P003.

## Required final status fields

- `WHERE_WE_ARE=`
- `SESSION_SEGMENT=LAC-P003`
- `PREDECESSOR_RESULT=OWNER_EXECUTION_PASS`
- `WHAT_WAS_VERIFIED=`
- `WHAT_WAS_COMPLETED=`
- `WHAT_REMAINS_IN_CURRENT_PHASE=`
- `TOTAL_PROJECT_POSITION=`
- `BLOCKERS=`
- `STOP_GATE=`
- `EXACT_NEXT_SAFE_ACTION=`
