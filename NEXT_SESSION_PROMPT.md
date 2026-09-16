# NEXT SESSION PROMPT — LOCAL AGENT CONTROLLER / B002 CALENDAR ADAPTER AGAINST PERMISSION MANAGEMENT

`SESSION_SEGMENT=LAC-B002`
`MODE=IMPLEMENTATION_SEGMENT`

Use the connected Web-File-Tool. Treat durable repository state and Git history as authority. This session owns **only** `LAC-B002`. Do not begin B003 or Chief of Staff.

## Mandatory first reads — exact order

1. `PROJECT_STATE.json`
2. `docs/ARCHITECTURE.md`
3. `UPSTREAM_LOCK.json`
4. `tasks/ACTIVE_TASK.md`
5. `docs/NEXT_SESSION_PROMPT_TEMPLATE.md`

Then read only what B002 requires, including:

- `docs/PERMISSION_MANAGEMENT.md`;
- `decisions/ADR-007_PERMISSION_ADMINISTRATION_AND_CAPABILITY_GOVERNANCE.md`;
- relevant Calendar sections of `docs/TECHNICAL_DESIGN_AND_IMPLEMENTATION_SPECIFICATION_v0.1.md`;
- capability/permission/effect sections of `docs/CONTRACTS.md`;
- `docs/P006_UAT_FIRST_USE_PERMISSION_DISCOVERY_QUALIFICATION.md`;
- `docs/P006_OWNER_UAT_OPERATOR_GUIDE.md`;
- `qualification/evidence/p006_uat_owner_execution.json`;
- B001 Gmail adapter/transport implementation and tests as the accepted generic external-service precedent;
- P001-P006/UAT code/tests needed to trace first-use discovery, exact approval, policy re-evaluation, dispatch, receipts, and non-resumption.

## Handoff facts to verify; do not assume

- `PREDECESSOR_ROLE=Lead Implementation Engineer`
- `PREDECESSOR_RESULT=P006_UAT_OWNER_EXECUTION_PASS`
- `P006_IMPLEMENTATION_COMMIT=ba39bbf1d73434b1b2071497f4ea6aab090681c6`
- `P006_UAT_IMPLEMENTATION_COMMIT=a67fb5ae5b722f995dc47fb658624b6ce49a968d`
- `HANDOFF_BASE_GIT_COMMIT=a67fb5ae5b722f995dc47fb658624b6ce49a968d`
- `OWNER_EXECUTION_EVIDENCE=qualification/evidence/p006_uat_owner_execution.json`
- `EXPECTED_PHASE=PHASE_4_PERMISSION_MANAGEMENT`
- `EXPECTED_ACTIVE_TASK=LAC-B002`
- `EXPECTED_NEXT_TASK=LAC-B003`

Verify the post-implementation handoff delta is limited to owner-execution evidence, durable state/task transition, and this successor prompt.

## Binding B002 first-use sequence

Calendar qualification must mechanically prove:

```text
fresh valid registered Calendar request
→ no applicable owner-configured standing permission/default
→ terminal DENY
→ bounded owner-reviewable NO_CONFIGURED_STANDING_PERMISSION item
→ no execution lease / no adapter mutation
→ owner configures scope through P004/P005
→ exact original request remains permanently closed
→ consumer issues a fresh Calendar request
→ current policy produces ALLOW, REQUIRE_APPROVAL, or DENY
→ adapter is reached only when currently authorized
```

An explicit configured `DENY`, including a matching default, must not generate recurring discovery work.

Do not treat the review item as `REQUIRE_APPROVAL`, do not add a fourth runtime state, and do not expose P004/P005 administration to the governed consumer.

## Scope discipline

No Chief of Staff business logic, B003 implementation, OpenClaw, Omarchy Agent OS, web/TUI, remote administration, enterprise RBAC, production Calendar credentials, or consequential production external effects.

The superseded pre-permission `LAC_B002_CALENDAR_ADAPTER_v0.1.0` owner package must not be executed or treated as current implementation authority.

## Required lifecycle

Follow the implementation lifecycle in `docs/NEXT_SESSION_PROMPT_TEMPLATE.md`: bounded predecessor verification, implement B002 completely, deterministic focused tests, accepted regression, correct in-scope defects, produce one owner-executable package, then stop at `OWNER_EXECUTION_REQUIRED`.

## Required final status fields

- `WHERE_WE_ARE=`
- `SESSION_SEGMENT=LAC-B002`
- `PREDECESSOR_RESULT=P006_UAT_OWNER_EXECUTION_PASS`
- `WHAT_WAS_VERIFIED=`
- `WHAT_WAS_COMPLETED=`
- `WHAT_REMAINS_IN_CURRENT_PHASE=`
- `TOTAL_PROJECT_POSITION=`
- `BLOCKERS=`
- `STOP_GATE=`
- `EXACT_NEXT_SAFE_ACTION=`
