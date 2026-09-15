# NEXT SESSION PROMPT — LOCAL AGENT CONTROLLER / P004 SECURE ADMIN API + OS IDENTITY BOUNDARY

`SESSION_SEGMENT=LAC-P004`
`MODE=IMPLEMENTATION_SEGMENT`

Use the connected Web-File-Tool. Treat durable repository state and Git history as authority. This session owns **only** `LAC-P004` secure local administrator API and Linux owner-identity boundary implementation. Do not begin P005, P006, Calendar, generic consumer B003, `lacctl`, or Chief of Staff implementation in this session.

## Mandatory first reads — exact order

1. `PROJECT_STATE.json`
2. `docs/ARCHITECTURE.md`
3. `UPSTREAM_LOCK.json`
4. `tasks/ACTIVE_TASK.md`
5. `docs/NEXT_SESSION_PROMPT_TEMPLATE.md`

Then read:

- `docs/PERMISSION_MANAGEMENT.md`;
- `decisions/ADR-007_PERMISSION_ADMINISTRATION_AND_CAPABILITY_GOVERNANCE.md`;
- `docs/CONTRACTS.md` capability/permission/admin sections;
- `qualification/evidence/p003_owner_execution.json` and `qualification/evidence/p003_test_output.txt`;
- P001 `packages/capabilities/` registry implementation;
- P002 quarantine/pending-permission implementation;
- P003 `packages/policy/standing.py`, dispatcher integration, and focused tests;
- only existing approval/state/sandbox interfaces and tests needed for P004.

## Handoff facts to verify; do not assume

- `PREDECESSOR_ROLE=Lead Implementation Engineer`
- `PREDECESSOR_RESULT=OWNER_EXECUTION_PASS`
- `PREDECESSOR_GIT_COMMIT=7ad316b9bee20eff468a0f6ff8437c68b817c9c6`
- `HANDOFF_BASE_GIT_COMMIT=3a5ebb342e9d6807b90bff66d3187327f2f36e3d`
- `OWNER_EXECUTION_EVIDENCE=qualification/evidence/p003_owner_execution.json`
- `BLOCKER_IDS=NONE`
- `EXPECTED_PHASE=PHASE_4_PERMISSION_MANAGEMENT`
- `EXPECTED_ACTIVE_TASK=LAC-P004`
- `EXPECTED_NEXT_TASK=LAC-P005`

P001 registration remains descriptive and grants zero authority. P002 unknown/new material is terminal `DENY`; pending permission is informational/admin work and never resumes a closed effect. P003 standing policy is deterministic over P002-validated trusted capability/resource/request metadata, with most-specific matching and equal-specificity precedence `DENY > REQUIRE_APPROVAL > ALLOW`. B001 Gmail remains accepted as a generic effect-adapter precursor. The prior `LAC_B002_CALENDAR_ADAPTER_v0.1.0` package remains superseded and must not be executed. Chief of Staff remains separate software.

## Required lifecycle

1. Perform bounded predecessor verification. Confirm P003 owner evidence is valid, the P003 implementation commit is in Git history, durable state/task/prompt are mutually consistent, P003 focused tests/regression evidence passed, and the live HEAD delta after the P003 implementation commit is handoff-only.
2. Implement `LAC-P004` completely as defined by `tasks/ACTIVE_TASK.md` and the binding permission-management design.
3. Preserve all LAC invariants plus P001 zero-authority registration, P002 terminal quarantine/non-resumability, P003 deterministic trusted-metadata-only conditions and precedence, and strict separation of runtime versus administration authority.
4. Use deterministic local/synthetic fixtures only. Do not use production credentials, production accounts, or external consequential effects.
5. Run focused P004 tests and the applicable accepted regression gate including P003, P002, P001, and B001; correct in-scope defects before handoff.
6. Produce one owner-executable package that completes P004 and activates fresh `LAC-P005` on success. Stop at `OWNER_EXECUTION_REQUIRED`; do not implement P005 in this conversation.

## Scope discipline

Do not add `lacctl`, permission-management E2E, Calendar, Chief of Staff E2E, OpenClaw, Omarchy Agent OS, web UI/TUI, remote administration, or enterprise RBAC in P004.

## Required final status fields

- `WHERE_WE_ARE=`
- `SESSION_SEGMENT=LAC-P004`
- `PREDECESSOR_RESULT=OWNER_EXECUTION_PASS`
- `WHAT_WAS_VERIFIED=`
- `WHAT_WAS_COMPLETED=`
- `WHAT_REMAINS_IN_CURRENT_PHASE=`
- `TOTAL_PROJECT_POSITION=`
- `BLOCKERS=`
- `STOP_GATE=`
- `EXACT_NEXT_SAFE_ACTION=`
