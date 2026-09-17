# ACTIVE TASK — LAC-PI001

## Task ID

`LAC-PI001`

## Objective

Build the first production-oriented **LAC-governed Pi v1 launch/profile** by joining the accepted real Pi path to the completed Phase 4 permission-aware consumer/runtime path.

A user who starts Pi through the LAC-supported launch/profile must get the normal Pi agent experience with LAC as the unavoidable authority/effect boundary for the governed effect surface. A user may still run ordinary standalone Pi separately; LAC makes no governance claim for a Pi process that was not launched in governed mode.

## In scope

- Reuse the exact pinned Pi 0.85.1 source/API boundary already qualified by A001-A004.
- Prefer Pi's own supported CLI/TUI/SDK/extension mechanisms for the user experience; do not build a competing general-purpose harness or chat UI.
- Preserve the accepted Pi sandbox/ambient-authority boundary: no unrestricted host filesystem, process, network, credential, controller-state, or administrator-socket access from the governed Pi process.
- Ensure the LAC-governed Pi process has only controller-backed consequential-effect tools; stock/direct effect tools must not provide a route around LAC.
- Replace the A003/A004 fixed-ALLOW effect bridge for the production path with the accepted Phase 4 capability/permission/external-consumer path or the thinnest equivalent composition of those accepted components.
- Keep principal, agent, application and skill identity controller-owned. Pi/model/tool arguments must not supply authority, approval, lease, executor, credential, policy or administrator identity.
- Give the Pi capability surface a canonical registered capability manifest. Registration grants zero authority.
- Route known-but-unconfigured, unknown/new capability, configured DENY, conditional ALLOW, REQUIRE_APPROVAL and ALLOW through the existing P001-P006 semantics.
- Make permission-required and permission-configuration outcomes visible to the human user rather than silently dropping them. The governed Pi/model process may observe bounded request/status information but cannot approve, reject, register capabilities, or mutate standing policy.
- For `REQUIRE_APPROVAL`, preserve the same canonical request while waiting/retrying so an exact owner approval can qualify, policy is re-evaluated immediately before dispatch, and the effect executes at most once.
- Preserve restart durability, terminal non-resumption, request ownership, exact approval binding, duplicate prevention, receipts, emergency pause, credential isolation and admin-surface isolation.
- Create deterministic positive and negative tests for the real Pi production path and retain the accepted regression chain.
- Produce one owner-executable package. Do not begin `LAC-PI002` in the same implementation session.

## Out of scope

- Any additional agent harness integration.
- Any external application/product implementation.
- A generic compatibility-protocol facade or gateway.
- Additional model-provider/runtime expansion.
- Replacing Pi with a new LAC-owned harness.
- Weakening sandbox isolation so Pi can directly reach the host or controller administrator surface.
- Redesigning accepted Phase 4 authority semantics.

## Required inputs

- `decisions/ADR-008_PI_V1_REFERENCE_HARNESS_AND_ROADMAP.md`
- Phase 5 requirements in `docs/TECHNICAL_DESIGN_AND_IMPLEMENTATION_SPECIFICATION_v0.1.md`
- `docs/ARCHITECTURE.md`
- `docs/A004_OWNER_BASELINE_UAT.md`
- `docs/P006_OWNER_UAT_OPERATOR_GUIDE.md`
- `docs/B003_EXTERNAL_CONSUMER_INTEGRATION.md`
- `docs/CONTRACTS.md`
- `docs/PERMISSION_MANAGEMENT.md`
- `packages/adapters/pi/adapter.py`
- `packages/adapters/pi/governed_pi.mjs`
- `packages/runtime/external_consumer.py`
- `scripts/a004_terminal.py`
- `scripts/a004_agent_worker.mjs`
- `scripts/a003_controller_bridge.py`
- current capability/policy/approval/dispatcher/state implementation and only the pinned Pi source needed to implement the supported launch/profile.

## Required outputs

- A supported LAC-governed Pi v1 launch/profile using the pinned Pi harness.
- Real Pi tool calls routed through the completed permission-aware LAC runtime rather than the old fixed-ALLOW qualification bridge.
- Human-visible bounded outcomes for ALLOW / REQUIRE_APPROVAL / DENY and permission-configuration discovery.
- Deterministic focused tests plus the full applicable accepted regression gate.
- Updated operator documentation showing how to start governed Pi and how that differs from ordinary standalone Pi.
- One owner-executable package using the established verify -> backup -> install -> test -> durable handoff pattern.
- On successful owner execution, durable transition to `LAC-PI002` owner UAT in a fresh session.

## Acceptance tests

- Governed launch proves the process is real pinned Pi and retains the accepted sandbox/ambient-authority restrictions.
- Governed Pi exposes no direct consequential-effect tool that bypasses LAC.
- A known registered action with no configured standing permission is terminally denied, creates/aggregates durable owner-reviewable pending work, is visibly reported to the user, and cannot resume after later configuration.
- An unknown/new capability request is terminally denied and queued without host effect.
- A configured `DENY` produces no adapter invocation and no recurring discovery noise.
- A configured conditional `ALLOW` executes only when the trusted deterministic condition matches.
- `REQUIRE_APPROVAL` creates a durable exact approval candidate; Pi cannot self-approve; owner approval alone does not execute; the same canonical request is re-evaluated and executes once only after valid approval.
- Mutation of security-relevant request material after approval fails closed.
- Duplicate/retry of a successful request does not repeat the effect.
- Restart preserves policy, pending work, exact approval/request binding, terminal state and receipt semantics.
- Cross-binding request/approval/status/receipt protections from P4-B002 remain intact.
- Governed Pi cannot access the owner administrator socket, service credentials, arbitrary host filesystem/process/network authority, or an alternate direct effect path.
- Ordinary standalone Pi remains launchable outside the governed profile and is explicitly not represented as LAC-governed.
- Accepted deterministic Phase 1-4 regression remains PASS.

## Package required?

Yes.

## Next task on success

`LAC-PI002` — real owner UAT of the production LAC-governed Pi path, including permission discovery, exact approval, deny, restart, duplicate prevention and bypass resistance. Do not begin it in the `LAC-PI001` implementation session.
