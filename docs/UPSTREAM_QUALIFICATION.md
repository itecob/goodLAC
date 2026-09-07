# Upstream Qualification — Phase 0 Candidate

## Revision policy

All candidates are pinned to exact source commits observed on 2026-09-05. Local qualification must fetch those exact commits, read the checked-out license files, record license hashes, and run the deterministic probes in `scripts/phase0_qualify.py`.

## Airlock code-level trace

Pinned source: `airlock-dev/airlock@68a71c7f0139c823971b95a79cf800e837630d3a` (`package.json` version 0.2.38).

Observed request path in the pinned implementation:

`allowlist -> exec-policy -> command-policy -> schema/arg checks -> detectors -> sandbox -> HITL gate -> execute`.

The HITL gate creates the approval payload from redacted request arguments, waits for an approval result, and on approval continues to the downstream execution middleware with the original live call context. The gate does not bind the approval to a canonical request hash, compare the approved security-relevant operation to the dispatch operation, or invoke policy evaluation again immediately before dispatch.

The HITL engine does provide useful lower-level behavior: pending requests are persisted to the audit database, approval timeouts are represented, approved/denied requests are removed from the pending maps, and pending requests are reconstructed from durable rows after restart.

### Binding consequence

Stock Airlock cannot satisfy INV-005 (exact approval binding) and INV-006 (immediate pre-dispatch policy re-evaluation) as the Lane B authority core. This is not a reason to fork Airlock. It remains useful as the Lane A compatibility gateway.

**Disposition: `AIRLOCK_WRAPPED`.**

The wrapper boundary is architectural: consequential typed effects terminate at the LAC Authority Core; Airlock does not become canonical authority for those effects.

## Secondary dispositions

- **Preloop:** Apache-2.0 broad self-hosted reference/lab candidate; too broad for v0.1 base.
- **agentgateway:** Apache-2.0 optional protocol gateway; deferred. A July 2026 high-severity advisory involving stateful MCP sessions crossing routes reinforces version-specific qualification before any future adoption.
- **Stonefold:** Apache-2.0 specification/TCK reference; its own project positioning is proof-of-concept rather than production-hardened trusted core.
- **Waggle:** conceptually relevant Pi-backed governance architecture, but no authoritative root license was found at the pinned revision. Concepts only; no code reuse. This is nonblocking because no code reuse is planned.
- **OpenClaw:** MIT future integration target. Pinned source contains dedicated execution approval-binding logic and mismatch tests for request context such as argv/cwd; reuse patterns only unless later code provenance is explicitly recorded.
- **Pi:** MIT at the pinned revision. Agent/coding tools are modular factories around `pi-agent-core`, supporting the Phase 3 plan to construct a harness with only controller-backed tools rather than unrestricted default tools.
- **FreeToken:** Apache-2.0 external local inference runtime; Phase 3 model endpoint only.
- **Cedar / OPA:** Apache-2.0 policy engine candidates; both deferred behind `PolicyDecisionProvider` until a concrete need earns inclusion.

## Phase 0 local evidence

The owner-executed package writes exact checkout, license, stable-tag/version discovery, source-probe, and targeted Airlock test results to `qualification/evidence/phase0.json` and `qualification/evidence/phase0.txt`.

## Airlock invariant-oriented capability assessment

The deterministic source probe records this matrix in `qualification/evidence/phase0.json` from the exact pinned checkout:

| Requirement | Phase 0 assessment of stock Airlock | LAC consequence |
|---|---|---|
| Exact request/approval binding | **No LAC canonical binding demonstrated** | Lane B must bind approval to LAC canonical request hash. |
| One-use approval | Pending HITL ticket is removed when decided | Useful Lane A behavior; not sufficient by itself for Lane B. |
| Approval expiry | HITL timeout is implemented | Reusable concept/compatibility behavior. |
| Pre-dispatch policy re-evaluation | **Not present in the pinned fixed chain** | Lane B must re-evaluate immediately before dispatch. |
| Durable approval state | Pending HITL rows are persisted/recovered | Useful, but LAC canonical lifecycle remains separate. |
| Idempotency | No LAC typed-effect idempotency guarantee demonstrated | LAC dispatcher/adapters own duplicate prevention. |
| Emergency pause | No LAC emergency-stop invariant demonstrated | LAC Authority Core owns pause state. |
| Credential isolation | Not a sufficient LAC effect-adapter credential boundary | Credentials remain outside agent/model context and generic shell. |
| Sandbox enforcement | Airlock has a sandbox stage in its tool pipeline | LAC still requires process-level ambient-authority isolation and Phase 2 bypass tests. |
| Crash/restart behavior | Pending approval recovery is present; LAC effect reconciliation is not provided | LAC state/lease/receipt lifecycle remains canonical. |
| Audit | Dispatch/success/error rows are emitted around downstream execution | Useful plumbing; audit never grants authority. |

This matrix is the reason `AIRLOCK_WRAPPED` is the least-invasive valid disposition rather than a fork, patch, or rejection.

## Build/test evidence policy

The owner-executed qualification records detected build manifests, declared runtime requirements, dependency counts where mechanically extractable, stable-tag discovery, checked-out license hashes, source probes, and component-check results in `UPSTREAM_LOCK.json` and `qualification/evidence/phase0.json`.

Airlock is the only upstream entering the Phase 0 adoption decision, so the package installs its pinned npm development dependencies and runs its relevant typecheck plus targeted HITL/core/agent-server upstream tests. Pi and FreeToken are future Phase 3 integrations: Phase 0 performs bounded source/package checks only and does not install their full future runtime stacks. In particular, FreeToken's CUDA/Torch inference test suite is deferred to Phase 3 because installing and exercising that GPU runtime would expand the active Phase 0 task into model-runtime integration. Deferred/reference components receive source/license/build-surface qualification only; they are not introduced into the v0.1 trusted computing base by this phase.

## Local/cloud and extension-point disposition

Phase 0 does not activate any upstream service or require production credentials. Airlock is qualified only as a local compatibility gateway candidate. Preloop remains a bounded self-hosted lab/reference comparison, agentgateway a deferred protocol gateway, Stonefold a specification/TCK source, and Waggle concepts-only. OpenClaw, Pi, and FreeToken are future integration targets; Cedar and OPA remain replaceable policy-provider candidates. Their exact build/dependency surfaces are recorded from their pinned checkouts, but none becomes canonical controller state or authority in Phase 0.
