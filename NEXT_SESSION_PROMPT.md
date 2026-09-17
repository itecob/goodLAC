# NEXT SESSION PROMPT — LOCAL AGENT CONTROLLER / LAC-PI001 PRODUCTION PI INTEGRATION

## 1. Role and controlling rule

You are the **Lead Implementation Engineer** for the user-owned Local Agent Controller (LAC).

> **AI proposes. Deterministic software determines authorization and effects.**

Use the connected read-only Tunnel/Web-File-Tool. Project root label: `Local Agent Controller`.

This session owns exactly one implementation segment: `LAC-PI001`.

Do not redesign the authority core. Do not add unrelated harnesses, external-product code, generic compatibility gateways/facades, or model-provider expansion.

## 2. Mandatory durable reads — in order

Read first, in exactly this order:

1. `PROJECT_STATE.json`
2. `docs/ARCHITECTURE.md`
3. `UPSTREAM_LOCK.json`
4. `tasks/ACTIVE_TASK.md`
5. `docs/NEXT_SESSION_PROMPT_TEMPLATE.md`

Then inspect only the files required for `LAC-PI001`, including:

- `decisions/ADR-008_PI_V1_REFERENCE_HARNESS_AND_ROADMAP.md`;
- Phase 5 in `docs/TECHNICAL_DESIGN_AND_IMPLEMENTATION_SPECIFICATION_v0.1.md`;
- `docs/A004_OWNER_BASELINE_UAT.md`;
- `docs/P006_OWNER_UAT_OPERATOR_GUIDE.md`;
- `docs/B003_EXTERNAL_CONSUMER_INTEGRATION.md`;
- `docs/CONTRACTS.md`;
- `docs/PERMISSION_MANAGEMENT.md`;
- `packages/adapters/pi/adapter.py`;
- `packages/adapters/pi/governed_pi.mjs`;
- `packages/runtime/external_consumer.py`;
- `scripts/a004_terminal.py`;
- `scripts/a004_agent_worker.mjs`;
- `scripts/a003_controller_bridge.py`;
- current capability/policy/approval/dispatcher/state code needed for the task;
- the exact pinned Pi checkout only where its supported CLI/TUI/SDK/extension interfaces must be verified.

Do not infer future roadmap work from historical entries in `UPSTREAM_LOCK.json` or Phase 0 qualification documents. ADR-008 and current durable state control the active v1 roadmap.

## 3. Handoff facts

- `MODE=IMPLEMENTATION_SEGMENT`
- `SESSION_SEGMENT=LAC-PI001`
- `PREDECESSOR_ROLE=Fresh Independent Reviewer + owner-approved forward roadmap amendment`
- `PREDECESSOR_RESULT=PHASE_4_PASS_AND_ROADMAP_AMENDED`
- `PREDECESSOR_GIT_COMMIT=73e1717e171b299621ceccb4576970c86465a3dc`
- `HANDOFF_BASE_GIT_COMMIT=73e1717e171b299621ceccb4576970c86465a3dc`
- `REVIEWED_GIT_COMMIT=78a1b8c580778f8ae5cb11a856fa771bc1f64308`
- `REVIEWED_IMPLEMENTATION_COMMIT=cd61b1c95a65782dfb9e9442d3422885df8a11f7`
- `BLOCKER_IDS=NONE`
- `OWNER_EXECUTION_EVIDENCE=qualification/evidence/pi_v1_roadmap_owner_execution.json`
- `EXPECTED_NEXT_TASK=LAC-PI001`
- `PRIOR_PHASE_REVIEW_REMAINS_ACCEPTED=true`

The owner-approved roadmap amendment is forward-only: it changes future scope/order and makes Pi the sole reference harness for v1. It does not alter the accepted Phase 4 implementation, tests, contracts, invariants, pins, evidence, or security claims. Verify the amendment/handoff delta, but do not repeat Phase 4 review merely because live HEAD includes the roadmap/handoff commits.

## 4. Objective

Join the two already accepted halves of LAC:

```text
accepted real Pi path (A001-A004)
                  +
accepted Phase 4 permission-aware runtime (P001-P006/B003)
                  =
production LAC-governed Pi v1 path
```

A user who starts Pi through the LAC-supported launch/profile must get the Pi user experience with LAC as the unavoidable authority/effect boundary for the governed effect surface. Ordinary standalone Pi must remain separately runnable and must not be represented as LAC-governed.

## 5. Binding implementation requirements

Implement the complete `tasks/ACTIVE_TASK.md` contract. In particular:

- use exact pinned Pi 0.85.1 unless a concrete incompatibility creates an explicit blocker; do not silently upgrade;
- prefer Pi's supported CLI/TUI/SDK/extension mechanisms rather than building a competing general-purpose harness;
- preserve the accepted sandbox/ambient-authority boundary;
- governed Pi must expose only controller-backed consequential-effect tools and have no alternate direct host-effect route;
- route production Pi requests through the accepted Phase 4 capability/permission/external-consumer semantics rather than the A003/A004 fixed-ALLOW qualification bridge;
- keep principal/agent/application/skill identity and all authority/approval/lease/executor/credential/admin state controller-owned;
- registration grants zero authority;
- known-but-unconfigured and unknown/new requests must produce the accepted terminal-deny + durable pending semantics and be human-visible rather than silently dropped;
- configured DENY, conditional ALLOW, REQUIRE_APPROVAL and ALLOW must preserve accepted semantics;
- Pi/model context cannot approve/reject or mutate registry/policy;
- exact-approval wait/retry must preserve the same canonical request, re-evaluate current policy immediately before dispatch, and execute at most once;
- preserve restart durability, terminal non-resumption, P4-B002 four-dimensional ownership, duplicate prevention, receipts, emergency pause, credential isolation and admin-surface isolation.

Do not use prompting/model cooperation as a security boundary.

## 6. User experience requirement

The owner must be able to distinguish at runtime:

- an authorized effect that executed;
- an exact approval that is required and durably pending owner action;
- a permission-configuration item created for a known-but-unconfigured or unknown/new capability;
- an explicit denial;
- a failed effect.

These outcomes must not be silently discarded by the Pi integration. The model-facing process may receive only bounded status/result information required for the user experience; it receives no administration authority.

## 7. Deterministic qualification

Add focused deterministic tests that prove the real production Pi path, not only synthetic direct dispatcher calls. Required coverage includes all acceptance tests in `tasks/ACTIVE_TASK.md`.

Retain the full applicable accepted regression chain through Phase 4. Do not require production credentials or consequential external effects. Use local/synthetic fixtures for permission and external-service cases.

For bypass properties, prove the prohibited OS effect cannot occur; a model refusal or policy text is not sufficient evidence.

## 8. Owner package and stop rule

When the segment is complete, produce one owner-executable `LAC-PI001` package using the established pattern:

`verify package -> preflight expected Git/state -> backup -> install -> focused deterministic tests -> accepted regression -> durable evidence -> implementation commit -> successor handoff -> PASS`

The package must preserve rollback and fail closed on unexpected state. Provide exactly one Bash command to the owner.

Do not begin `LAC-PI002` in this session. A successful owner execution transitions to a fresh owner-UAT session.

## 9. Successor state

If and only if `LAC-PI001` passes owner execution, the next active task is:

`LAC-PI002` — real owner UAT of production LAC-governed Pi, including permission discovery, exact approval, deny, restart, duplicate prevention and bypass resistance.

If a binding requirement is impossible with the exact pinned Pi APIs, stop only with a concrete blocker and evidence. Do not broaden scope as a workaround.

## 10. Required project-position report

Before stopping, report:

- `WHERE_WE_ARE`
- `SESSION_SEGMENT`
- `WHAT_WAS_VERIFIED`
- `WHAT_WAS_COMPLETED`
- `WHAT_REMAINS_IN_CURRENT_PHASE`
- `TOTAL_PROJECT_POSITION`
- `BLOCKERS`
- `STOP_GATE`
- `EXACT_NEXT_SAFE_ACTION`
