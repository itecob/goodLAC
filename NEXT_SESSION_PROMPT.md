# NEXT SESSION PROMPT — LOCAL AGENT CONTROLLER / P005 LACCTL ADMINISTRATION CLIENT

`SESSION_SEGMENT=LAC-P005`
`MODE=IMPLEMENTATION_SEGMENT`

Use the connected Web-File-Tool. Treat durable repository state and Git history as authority. This session owns **only** `LAC-P005` first authoritative `lacctl` local administration client consuming the accepted P004 admin API. Do not begin P006, Calendar, generic consumer B003, Chief of Staff, web/TUI, remote administration, or enterprise RBAC in this session.

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
- `docs/ADMIN_API.md`;
- `qualification/evidence/p004_owner_execution.json` and `qualification/evidence/p004_test_output.txt`;
- P004 `packages/admin/` implementation and focused tests;
- only P001–P003/approval interfaces needed to verify that `lacctl` does not bypass P004.

## Handoff facts to verify; do not assume

- `PREDECESSOR_ROLE=Lead Implementation Engineer`
- `PREDECESSOR_RESULT=OWNER_EXECUTION_PASS`
- `PREDECESSOR_GIT_COMMIT=8ce358cc302f698ccda405c7b4f5953aca109677`
- `HANDOFF_BASE_GIT_COMMIT=4cfa9508fb0bd997cc6bcaf8c535e3e8344bb521`
- `OWNER_EXECUTION_EVIDENCE=qualification/evidence/p004_owner_execution.json`
- `BLOCKER_IDS=NONE`
- `EXPECTED_PHASE=PHASE_4_PERMISSION_MANAGEMENT`
- `EXPECTED_ACTIVE_TASK=LAC-P005`
- `EXPECTED_NEXT_TASK=LAC-P006`

P001 registration remains descriptive and grants zero authority. P002 unknown/new material remains terminal `DENY`; pending permission is informational/admin work and never resumes a closed effect. P003 standing policy remains deterministic over P002-validated trusted metadata with precedence `DENY > REQUIRE_APPROVAL > ALLOW`. P004 is the only accepted administrator mutation boundary: owner-only local Unix-domain socket, controller-observed peer UID before request parsing, no admin socket exposure inside governed agent sandboxes. `lacctl` must consume P004 rather than becoming a direct state writer. B001 Gmail remains accepted; the old unexecuted B002 package remains superseded. Chief of Staff remains separate software.

## Required lifecycle

1. Perform bounded predecessor verification. Confirm P004 owner evidence is valid, the P004 implementation commit is in Git history, durable state/task/prompt are mutually consistent, focused tests/regression passed, and the live HEAD delta after the P004 implementation commit is handoff-only.
2. Implement `LAC-P005` completely as defined by `tasks/ACTIVE_TASK.md`.
3. Preserve all LAC invariants plus P001 zero-authority registration, P002 terminal quarantine/non-resumability, P003 deterministic trusted-metadata-only policy, and P004 strict runtime-versus-administration separation.
4. Use deterministic local/synthetic fixtures only. Do not use production credentials, production accounts, or external consequential effects.
5. Run focused P005 tests and the applicable accepted regression gate including P004, P003, P002, P001, and B001; correct in-scope defects before handoff.
6. Produce one owner-executable package that completes P005 and activates fresh `LAC-P006` on success. Stop at `OWNER_EXECUTION_REQUIRED`; do not implement P006 in this conversation.

## Scope discipline

Do not add P006 qualification early, Calendar, Chief of Staff E2E, OpenClaw, Omarchy Agent OS, web UI/TUI, remote administration, or enterprise RBAC in P005.

## Required final status fields

- `WHERE_WE_ARE=`
- `SESSION_SEGMENT=LAC-P005`
- `PREDECESSOR_RESULT=OWNER_EXECUTION_PASS`
- `WHAT_WAS_VERIFIED=`
- `WHAT_WAS_COMPLETED=`
- `WHAT_REMAINS_IN_CURRENT_PHASE=`
- `TOTAL_PROJECT_POSITION=`
- `BLOCKERS=`
- `STOP_GATE=`
- `EXACT_NEXT_SAFE_ACTION=`
