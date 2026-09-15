# NEXT SESSION PROMPT — LOCAL AGENT CONTROLLER / P001 CAPABILITY REGISTRY

`SESSION_SEGMENT=LAC-P001`
`MODE=IMPLEMENTATION_SEGMENT`

Use the connected Web-File-Tool. Treat durable repository state and Git history as authority. This session owns **only** `LAC-P001` capability/skill registry and manifest-contract implementation. Do not begin P002, Calendar B002, generic consumer B003, or Chief of Staff implementation in this session.

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
- `docs/TECHNICAL_DESIGN_AND_IMPLEMENTATION_SPECIFICATION_v0.1.md` only as needed for binding invariants/Phase 4;
- `qualification/evidence/permission_management_amendment_owner_execution.json` if present;
- only the existing state-store/policy/effect interfaces and tests needed for P001.

## Handoff facts to verify; do not assume

- `PREDECESSOR_ROLE=Owner-authorized architecture/workflow amendment`
- `PREDECESSOR_RESULT=OWNER_EXECUTION_PASS`
- `PREDECESSOR_GIT_COMMIT=__AMENDMENT_COMMIT__`
- `HANDOFF_BASE_GIT_COMMIT=cf29191ae05490f94e74cae9d0006f8324bebab0`
- `OWNER_EXECUTION_EVIDENCE=qualification/evidence/permission_management_amendment_owner_execution.json`
- `BLOCKER_IDS=NONE`
- `EXPECTED_PHASE=PHASE_4_PERMISSION_MANAGEMENT`
- `EXPECTED_ACTIVE_TASK=LAC-P001`
- `EXPECTED_NEXT_TASK=LAC-P002`

B001 Gmail remains accepted as a generic effect-adapter precursor. The prior `LAC_B002_CALENDAR_ADAPTER_v0.1.0` package was explicitly superseded before execution. Do not implement Calendar in P001. Chief of Staff is separate software and is not implemented in the LAC repository.

## Required lifecycle

1. Perform bounded predecessor verification. Confirm the amendment evidence is valid, durable state/task/prompt are mutually consistent, the amendment commit is in Git history, and the live HEAD delta after the amendment commit is handoff-only.
2. Implement `LAC-P001` completely as defined by `tasks/ACTIVE_TASK.md` and the binding permission-management design.
3. Preserve all existing LAC invariants plus: registration grants no authority; unknown material fails closed; runtime consumers cannot administer policy/registry; later policy changes never revive closed effects.
4. Use deterministic local/synthetic fixtures. Do not use production credentials or external consequential effects.
5. Run focused P001 tests and the applicable accepted regression gate including B001; correct in-scope defects before handoff.
6. Produce one owner-executable package that completes P001 and activates fresh `LAC-P002` on success. Stop at `OWNER_EXECUTION_REQUIRED`; do not implement P002 in this conversation.

## Scope discipline

Do not add the pending-permission queue, scoped conditional policy evaluator, admin socket/API, `lacctl`, Calendar, Chief of Staff E2E, OpenClaw, Omarchy Agent OS, web UI/TUI, or enterprise RBAC in P001.

## Required final status fields

- `WHERE_WE_ARE=`
- `SESSION_SEGMENT=LAC-P001`
- `PREDECESSOR_RESULT=OWNER_EXECUTION_PASS`
- `WHAT_WAS_VERIFIED=`
- `WHAT_WAS_COMPLETED=`
- `WHAT_REMAINS_IN_CURRENT_PHASE=`
- `TOTAL_PROJECT_POSITION=`
- `BLOCKERS=`
- `STOP_GATE=`
- `EXACT_NEXT_SAFE_ACTION=`
