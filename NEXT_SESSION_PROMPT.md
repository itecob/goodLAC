# NEXT SESSION PROMPT — LOCAL AGENT CONTROLLER / P006 PERMISSION-MANAGEMENT E2E SECURITY QUALIFICATION

`SESSION_SEGMENT=LAC-P006`
`MODE=IMPLEMENTATION_SEGMENT`

Use the connected Web-File-Tool. Treat durable repository state and Git history as authority. This session owns **only** `LAC-P006` permission-management end-to-end and negative-security qualification of P001–P005. Do not begin Calendar/B002, B003, Chief of Staff, web/TUI, remote administration, or enterprise RBAC in this session.

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
- `docs/LACCTL.md`;
- `qualification/evidence/p005_owner_execution.json` and `qualification/evidence/p005_test_output.txt`;
- P005 `packages/lacctl/`, `scripts/lacctl`, focused tests, and `scripts/test-p005`;
- only the P001–P004/approval/runtime/sandbox interfaces needed to execute the qualification scenarios.

## Handoff facts to verify; do not assume

- `PREDECESSOR_ROLE=Lead Implementation Engineer`
- `PREDECESSOR_RESULT=OWNER_EXECUTION_PASS`
- `PREDECESSOR_GIT_COMMIT=9c385ab1e23a13d608e9b6567d68a6c76aa8bb73`
- `HANDOFF_BASE_GIT_COMMIT=9e5e22957322f9caeba3b7e337cdee88ba7ea065`
- `OWNER_EXECUTION_EVIDENCE=qualification/evidence/p005_owner_execution.json`
- `BLOCKER_IDS=NONE`
- `EXPECTED_PHASE=PHASE_4_PERMISSION_MANAGEMENT`
- `EXPECTED_ACTIVE_TASK=LAC-P006`
- `EXPECTED_NEXT_TASK=LAC-B002`

P001 registration remains descriptive and grants zero authority. P002 unknown/new material remains terminal `DENY`; pending permission is informational/admin work and never resumes a closed effect. P003 standing policy remains deterministic over P002-validated trusted metadata with precedence `DENY > REQUIRE_APPROVAL > ALLOW`. P004 remains the only accepted administrator mutation boundary: owner-only local Unix-domain socket, controller-observed peer UID before request parsing, no admin socket exposure inside governed agent sandboxes. P005 `lacctl` is a thin P004 protocol client with no canonical-state write path. B001 Gmail remains accepted; the old unexecuted B002 package remains superseded. Chief of Staff remains separate software.

## Required lifecycle

1. Perform bounded predecessor verification. Confirm P005 owner evidence is valid, the P005 implementation commit is in Git history, durable state/task/prompt are mutually consistent, focused tests/regression passed, and the live HEAD delta after the P005 implementation commit is handoff-only.
2. Execute `LAC-P006` completely as defined by `tasks/ACTIVE_TASK.md`. This is qualification, not a feature-expansion task.
3. Use deterministic local/synthetic fixtures only. Do not use production credentials, production accounts, third-party systems, or external consequential effects.
4. Establish actual negative-security outcomes, not policy labels alone: prove closed P002 effects remain closed; prove governed runtime/sandbox surfaces cannot reach the admin endpoint; prove rejected/unavailable/malformed admin paths cause no canonical mutation.
5. Run focused P006 tests and the applicable accepted regression gate through P005/P004/P003/P002/P001/B001 and prior accepted phases. Correct only concrete in-scope defects required by existing binding contracts, then rerun affected gates.
6. Produce one owner-executable package that completes P006 and activates fresh `LAC-B002` on success. Stop at `OWNER_EXECUTION_REQUIRED`; do not implement B002 in this conversation.

## Scope discipline

Do not add Calendar/B002 early, B003, Chief of Staff E2E, OpenClaw, Omarchy Agent OS, web UI/TUI, remote administration, enterprise RBAC, or new permission features not required by an existing binding contract.

## Required final status fields

- `WHERE_WE_ARE=`
- `SESSION_SEGMENT=LAC-P006`
- `PREDECESSOR_RESULT=OWNER_EXECUTION_PASS`
- `WHAT_WAS_VERIFIED=`
- `WHAT_WAS_COMPLETED=`
- `WHAT_REMAINS_IN_CURRENT_PHASE=`
- `TOTAL_PROJECT_POSITION=`
- `BLOCKERS=`
- `STOP_GATE=`
- `EXACT_NEXT_SAFE_ACTION=`
