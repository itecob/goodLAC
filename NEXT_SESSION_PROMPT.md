# NEXT SESSION PROMPT — LOCAL AGENT CONTROLLER / B002 CALENDAR GENERIC ADAPTER AGAINST PERMISSION MANAGEMENT

`SESSION_SEGMENT=LAC-B002`
`MODE=IMPLEMENTATION_SEGMENT`

Use the connected Web-File-Tool. Treat durable repository state and Git history as authority. This session owns **only** `LAC-B002`: the generic Calendar typed-effect adapter integrated with the completed P001-P006 permission-management plane. Do not begin B003, Chief of Staff, web/TUI, remote administration, OpenClaw, Omarchy Agent OS, or enterprise RBAC in this session.

## Mandatory first reads — exact order

1. `PROJECT_STATE.json`
2. `docs/ARCHITECTURE.md`
3. `UPSTREAM_LOCK.json`
4. `tasks/ACTIVE_TASK.md`
5. `docs/NEXT_SESSION_PROMPT_TEMPLATE.md`

Then read:

- `docs/PERMISSION_MANAGEMENT.md`;
- `decisions/ADR-007_PERMISSION_ADMINISTRATION_AND_CAPABILITY_GOVERNANCE.md`;
- Calendar and Phase 4 sections of `docs/TECHNICAL_DESIGN_AND_IMPLEMENTATION_SPECIFICATION_v0.1.md`;
- `docs/CONTRACTS.md` capability/permission/effect sections;
- `docs/P006_PERMISSION_MANAGEMENT_QUALIFICATION.md`;
- `qualification/evidence/p006_owner_execution.json` and `qualification/evidence/p006_test_output.txt`;
- the accepted B001 Gmail adapter/tests as the generic external-service adapter pattern;
- P001-P006 interfaces needed to route Calendar requests through capability validation, standing policy, exact approval, dispatch, credentials, receipts, and reconciliation.

## Handoff facts to verify; do not assume

- `PREDECESSOR_ROLE=Lead Implementation Engineer`
- `PREDECESSOR_RESULT=OWNER_EXECUTION_PASS`
- `PREDECESSOR_GIT_COMMIT=ba39bbf1d73434b1b2071497f4ea6aab090681c6`
- `HANDOFF_BASE_GIT_COMMIT=2272fc81bb88f97892630eff1076676802c599cf`
- `OWNER_EXECUTION_EVIDENCE=qualification/evidence/p006_owner_execution.json`
- `BLOCKER_IDS=NONE`
- `EXPECTED_PHASE=PHASE_4_PERMISSION_MANAGEMENT`
- `EXPECTED_ACTIVE_TASK=LAC-B002`
- `EXPECTED_NEXT_TASK=LAC-B003`

P001 registration remains zero-authority. P002 unknown/new material remains terminal `DENY` and non-resumable. P003 standing policy remains deterministic with `DENY > REQUIRE_APPROVAL > ALLOW`; only P002-validated trusted metadata is policy-addressable. P004/P005 remain the isolated owner administration boundary/client and are not runtime authority. P006 qualification must remain passing. Its nested prior-phase regression is deterministic: accepted A003/A004 live evidence is verified while current deterministic security/interface conformance is rerun; direct A003/A004 test scripts still default to live mode. B001 Gmail remains accepted. The old unexecuted Calendar package remains superseded. Chief of Staff remains separate software.

## Required lifecycle

1. Perform bounded predecessor verification. Confirm P006 owner evidence is valid, the P006 implementation commit is in Git history, durable state/task/prompt are mutually consistent, focused tests/regression passed, and the live HEAD delta after the P006 implementation commit is handoff-only.
2. Execute `LAC-B002` completely as defined by `tasks/ACTIVE_TASK.md`.
3. Implement Calendar as generic typed effects reusable by any authorized consumer. Route permission-aware Calendar requests through the completed capability/standing-policy/exact-approval dispatcher path; do not create a Calendar-specific authority bypass.
4. Use deterministic synthetic/local transport fixtures only. Do not use production Google credentials/accounts/calendars or external consequential effects.
5. Bind calendar, title, start, end, timezone, attendees, location, recurrence, and conference settings into canonical mutation authority. Demonstrate that security-relevant mutation invalidates approval.
6. Preserve credential isolation and fail closed on malformed/unknown actions, unsupported resources/accounts, credential-shaped provider output, and ambiguous mutation reconciliation. `calendar.delete` remains denied/no mutation implementation unless an existing binding contract requires otherwise.
7. Run focused B002 tests and the applicable accepted regression gate through P006/P005/P004/P003/P002/P001/B001 and prior accepted phases. Correct only concrete in-scope defects required by existing binding contracts, then rerun affected gates.
8. Produce one owner-executable package that completes B002 and activates fresh `LAC-B003` on success. Stop at `OWNER_EXECUTION_REQUIRED`; do not implement B003 in this conversation.

## Scope discipline

Do not add Chief of Staff workflow/business logic, B003 early, OpenClaw, Omarchy Agent OS, web UI/TUI, remote administration, enterprise RBAC, or new permission features not required by an existing binding contract.

## Required final status fields

- `WHERE_WE_ARE=`
- `SESSION_SEGMENT=LAC-B002`
- `PREDECESSOR_RESULT=OWNER_EXECUTION_PASS`
- `WHAT_WAS_VERIFIED=`
- `WHAT_WAS_COMPLETED=`
- `WHAT_REMAINS_IN_CURRENT_PHASE=`
- `TOTAL_PROJECT_POSITION=`
- `BLOCKERS=`
- `STOP_GATE=`
- `EXACT_NEXT_SAFE_ACTION=`
