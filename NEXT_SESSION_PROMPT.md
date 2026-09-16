# NEXT SESSION PROMPT — LOCAL AGENT CONTROLLER / P006 OWNER UAT + FIRST-USE PERMISSION DISCOVERY REMEDIATION

`SESSION_SEGMENT=LAC-P006-UAT`
`MODE=IMPLEMENTATION_AND_OWNER_UAT_REMEDIATION`

Use the connected Web-File-Tool. Treat durable repository state and Git history as authority. This session owns **only** the owner-UAT/remediation gate inserted after accepted P006 and before B002. Do not begin the Calendar adapter until this gate completes.

## Mandatory first reads — exact order

1. `PROJECT_STATE.json`
2. `docs/ARCHITECTURE.md`
3. `UPSTREAM_LOCK.json`
4. `tasks/ACTIVE_TASK.md`
5. `docs/NEXT_SESSION_PROMPT_TEMPLATE.md`

Then read:

- `docs/PERMISSION_MANAGEMENT.md`;
- `decisions/ADR-007_PERMISSION_ADMINISTRATION_AND_CAPABILITY_GOVERNANCE.md`;
- permission-management sections of `docs/TECHNICAL_DESIGN_AND_IMPLEMENTATION_SPECIFICATION_v0.1.md`;
- capability/permission/effect sections of `docs/CONTRACTS.md`;
- `docs/P006_PERMISSION_MANAGEMENT_QUALIFICATION.md`;
- `docs/P006_OWNER_UAT_OPERATOR_GUIDE.md`;
- `qualification/evidence/p006_owner_execution.json` and `qualification/evidence/p006_test_output.txt`;
- `scripts/lac-owner-tour` and `scripts/p006_owner_permission_demo.py`;
- P001-P006 implementation/tests needed to trace capability validation, pending records, standing-policy fallback, admin mutation, exact approval, dispatch, receipts, and non-resumption.

## Handoff facts to verify; do not assume

- `PREDECESSOR_RESULT=P006_OWNER_EXECUTION_PASS`
- `P006_IMPLEMENTATION_COMMIT=ba39bbf1d73434b1b2071497f4ea6aab090681c6`
- `P006_HANDOFF_COMMIT=abd3ebf8a7e676f4a81f51b3566dae3394247aeb`
- `OWNER_EXECUTION_EVIDENCE=qualification/evidence/p006_owner_execution.json`
- `EXPECTED_PHASE=PHASE_4_PERMISSION_MANAGEMENT`
- `EXPECTED_ACTIVE_TASK=LAC-P006-UAT`
- `EXPECTED_NEXT_TASK=LAC-B002`

Confirm the sequence-amendment delta after `abd3ebf8a7e676f4a81f51b3566dae3394247aeb` is limited to this owner-UAT gate, operator tooling/docs, and handoff state.

## Newly binding owner requirement

The previous binding permission design guarantees pending-permission records for unknown/new capability/resource/material. The owner has now clarified an additional first-use requirement that must hold before B002:

```text
fresh request for registered/known capability
→ capability/resource/material validates
→ no applicable user-configured standing permission/default exists
→ terminal DENY for this effect
→ no lease / no adapter effect
→ create or aggregate a bounded owner-reviewable permission-configuration item
→ original request remains permanently closed
→ owner configures future standing permission through P004/P005
→ consumer issues a fresh request
→ fresh request is evaluated against current policy
```

This is **not** `REQUIRE_APPROVAL`, not a waiting effect, and not a fourth runtime outcome. The enforcement result remains `DENY`. The administrative record exists only to make an unconfigured permission discoverable and actionable by the owner.

An explicit configured `DENY`, including a matching configured default, is already an owner decision and must not be converted into recurring permission-review noise.

The review item must be bounded, deterministic, deduplicated/aggregated, credential-safe, and based only on trusted registered capability/resource/request metadata. It must expose enough scope for an informed owner decision. It must not give the runtime consumer access to P004/P005 administration.

## Required lifecycle

1. Verify accepted P006 state/evidence and the sequence-amendment delta.
2. Use the owner-tour tooling and any owner-provided terminal output to establish what the user can currently see and operate.
3. Reproduce the known-capability/no-configured-policy behavior mechanically. Do not infer it only from docs.
4. If the current implementation lacks the newly binding owner-review item, implement the smallest deterministic remediation consistent with existing authority invariants. Update binding docs/contracts/tests as required.
5. Preserve: P001 registration zero authority; P002 closed-effect non-resumption; P003 deterministic precedence and explicit DENY; P004/P005 isolation; exact approval binding; pre-dispatch re-evaluation; durable truth; idempotency; fail closed; no credentials in agent context; no admin surface in governed runtime.
6. Run focused tests and the accepted deterministic regression through P006 and prior phases.
7. Ensure the owner walkthrough remains usable after remediation and clearly demonstrates the corrected first-use behavior.
8. Produce one owner-executable package completing `LAC-P006-UAT` and activating fresh `LAC-B002` only on PASS.
9. The B002 handoff must explicitly require this Calendar sequence: first-use request is denied and surfaced for owner permission scoping; owner configures scope; original request is proven non-resumable; a fresh Calendar request is issued; only then does current policy yield `ALLOW`, `REQUIRE_APPROVAL`, or `DENY` and reach the adapter where authorized.
10. Stop at `OWNER_EXECUTION_REQUIRED`. Do not implement B002 in this session.

## Scope discipline

No Calendar implementation, Chief of Staff business logic, B003, OpenClaw, Omarchy Agent OS, web/TUI, remote administration, enterprise RBAC, production external credentials, or consequential external effects.

## Required final status fields

- `WHERE_WE_ARE=`
- `SESSION_SEGMENT=LAC-P006-UAT`
- `PREDECESSOR_RESULT=P006_OWNER_EXECUTION_PASS`
- `WHAT_WAS_VERIFIED=`
- `WHAT_WAS_COMPLETED=`
- `WHAT_REMAINS_IN_CURRENT_PHASE=`
- `TOTAL_PROJECT_POSITION=`
- `BLOCKERS=`
- `STOP_GATE=`
- `EXACT_NEXT_SAFE_ACTION=`
