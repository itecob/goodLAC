# Architecture — Controlling Baseline v0.1

This file is the concise operating architecture derived from the controlling Technical Design and Implementation Specification v0.1, the accepted Phase 4 permission-management amendment, and ADR-008. It does not broaden the product into an assistant, workflow engine, or general-purpose harness.

## Central rule

The AI proposes. Deterministic software authorizes and permits effects.

## Product separation

Local Agent Controller is an independent reusable authority/effect-control product. Pi is the sole reference harness for the active LAC v1 roadmap, but Pi does not own LAC authority semantics.

LAC may contain generic service effect adapters and the native local consumer/runtime contract needed by governed clients. It must not absorb application workflow, memory, prioritization, briefing, or unrelated product logic.

Ordinary standalone Pi may still be run independently. A Pi process is represented as **LAC-governed** only when it is started through the qualified LAC launch/profile that removes alternate consequential-effect paths and binds the process to the controller-owned runtime boundary.

## Local-first contract

Canonical controller state, capability registry, pending-permission records, policy, identity, effect lifecycle, approvals, leases, audit, receipts, emergency pause, credential references, execution boundaries, and local model routing configuration remain local. Remote systems may be effect destinations but are not required for controller governance.

## Two lanes

**Lane A — compatibility governance:** raw compatibility/tool calls may pass through a lower-assurance compatibility gateway where explicitly configured.

**Lane B — typed governed effects:** consequential operations enter the LAC Authority Core as versioned typed effect requests, are canonicalized, authenticated, capability-validated, policy-evaluated, approval-bound when required, re-evaluated immediately before dispatch, leased, and executed by bounded effect adapters.

The v1 Pi reference path uses the strongest available typed governed-effect path for consequential effects. Merely making LAC callable from a process does not make that process governed; bypass resistance is a separate requirement.

## Runtime versus administration surfaces

LAC exposes logically separate control surfaces:

- **Runtime surface:** governed consumers submit effect requests and inspect permitted request/result state. Runtime consumers cannot mutate capability registration, standing policy, administrator identity, or controller invariants.
- **Administration surface:** the human owner manages capability registration, pending permission requests, standing policy, revocation, and exact approvals. v0.1 uses a separate owner-only Linux Unix-domain admin socket with peer-UID verification and no exposure inside governed agent sandboxes.

The first authoritative administration client is `lacctl`. Future user interfaces must consume the same admin API and never become canonical state writers.

## Permission-management contract

Capability registration, standing permission, and exact effect approval are distinct.

- Registration describes what a skill/application may request and grants zero authority.
- Standing policy returns only `ALLOW`, `REQUIRE_APPROVAL`, or `DENY`. User-facing `ASK` maps to `REQUIRE_APPROVAL`.
- Exact approval binds one canonical operation when required.
- Unknown/new capability, resource scope, or material argument shape is terminally denied and recorded in a bounded pending-permission queue. Resolving the queue item changes only future policy; the denied effect never resumes.
- A valid registered capability/resource/material request with no applicable user-configured standing rule or default is also terminally `DENY`, with no lease or adapter effect, and creates/aggregates bounded owner-reviewable permission-configuration work. An explicit configured `DENY` rule/default is already an owner decision and does not create this discovery work. Configuration changes affect only a fresh request.

Conditional “allow unless / ask when” behavior is implemented through deterministic rules over trusted capability/resource/request metadata, never through model judgment.

### Permission-gated workflow continuation

ADR-009 adds a Phase 5 consumer-workflow rule without changing Phase 4 authority semantics.
A terminal permission-configuration denial may cause the governed host to suspend the user
workflow, but the denied effect itself remains permanently closed.

A continuation is non-authoritative. After owner policy configuration it may submit at most one
fresh canonical request derived from immutable captured intent. That fresh request has new
request/idempotency identity and must pass complete current capability, policy, approval,
emergency, dispatch and sandbox evaluation. Mutation is a new proposal, not continuation.
Restart may recover blocked workflow state but never auto-dispatch an effect.

## Pi v1 reference-harness contract

The production Pi integration must join the accepted real Pi path to the accepted Phase 4 permission-aware runtime.

A governed Pi launch/profile must satisfy all of the following:

- use the exact qualified Pi revision unless a later task explicitly re-qualifies an upgrade;
- prefer Pi's supported CLI/TUI/SDK/extension mechanisms rather than creating a competing LAC harness;
- expose only controller-backed consequential-effect tools;
- preserve the qualified process sandbox and ambient filesystem/process/network/environment restrictions;
- keep principal, agent, application and skill identity controller-owned;
- route capability validation, standing policy, pending permission discovery, exact approval, dispatch, leases, receipts and emergency pause through canonical LAC state;
- make `ALLOW`, `REQUIRE_APPROVAL`, `DENY` and permission-configuration outcomes human-visible without giving the model-facing process administration authority;
- preserve canonical request identity across an exact-approval wait/retry so the approved effect is re-evaluated and can execute at most once;
- retain durable restart and non-resumption semantics;
- for permission-configuration denial, suspend the governed workflow before the model can continue, then use only a one-shot fresh-request continuation after owner resolution; never revive the denied request;
- never describe ordinary standalone Pi as LAC-governed.

Pi-specific integration code is an edge adapter. It must not become a second policy/approval/state authority.

## Binding invariants

- INV-001 no implicit authority.
- INV-002 model output is never authorization.
- INV-003 governed mode has no alternate consequential-effect bypass.
- INV-004 service credentials do not enter agent context.
- INV-005 approval binds the exact canonical security-relevant operation; security-relevant mutation invalidates approval.
- INV-006 policy is re-evaluated immediately before dispatch.
- INV-007 deny wins: `DENY > REQUIRE_APPROVAL > ALLOW` for equal-precedence conflict.
- INV-008 consequential effects are idempotent where possible; controller prevents duplicates otherwise.
- INV-009 controller durable state is operational truth.
- INV-010 unknown state/action/adapter/resource/principal/approval/execution fails closed.
- INV-011 local emergency pause blocks new consequential effects without erasing inspection state.
- INV-012 audit never grants authority.
- INV-013 raw compatibility governance is explicitly lower assurance than typed effects.
- INV-014 deterministic work stays deterministic after typed intent translation.
- INV-015 capability/skill registration grants no authority.
- INV-016 an unknown/new capability, resource scope, or material request shape is terminally denied; a pending-permission record is informational/admin work, not a resumable effect.
- INV-017 policy/capability administration is unavailable through the agent runtime and requires the isolated administrator surface.
- INV-018 later policy/registry changes never revive a previously denied, rejected, expired, or otherwise closed effect.
- INV-019 a valid registered request with no applicable user-configured standing permission fails closed as `DENY` and creates bounded owner-reviewable configuration work; explicit configured `DENY` creates no recurring discovery noise.
- INV-020 workflow continuation after permission configuration is non-authoritative: the original denied effect remains closed, and any continuation uses exactly one fresh request that receives complete current authority evaluation before any effect.

## Required internal interfaces

`AgentAdapter`, `ModelProvider`, `PolicyDecisionProvider`, `ApprovalSurface`, `EffectAdapter`, `SandboxBackend`, `SecretProvider`, `AuditSink`, `StateStore`, `CapabilityRegistry`, and the isolated administration surface.

## State and execution

SQLite WAL remains the single-machine durable store. An approval never transitions directly to execution; it must pass pre-dispatch policy re-evaluation and then a short-lived transactional execution lease. Permission/registry mutations are atomic, revisioned, auditable controller state and cannot mutate terminal effects.

Non-authoritative consumer continuation state, when present, is not authority truth and cannot
grant permission, approval, lease, or dispatch. It exists only to recover a blocked user workflow
and construct a fresh proposal/request after trusted owner resolution.

## Sandbox and credentials

Governed tools alone are insufficient. The agent process must have bounded ambient filesystem/process/network/environment authority using an established Linux sandbox. Agents receive credential references, not credentials. Governed agent sandboxes must not expose the administration socket.

## Accepted foundation and active v1 sequence

Accepted foundation:

`Phase 1 authority core -> Phase 2 local enforcement -> Phase 3 real Pi/local model -> Phase 4 permission management + generic consumer contract -> Phase 4 fresh independent review PASS`.

Active v1 sequence:

`LAC-PI001 -> LAC-PI002 -> LAC-PI002-D001 -> LAC-PI003 -> phase-boundary independent review -> LAC-V001 productization`.

No additional harness integration, external-product implementation, generic compatibility-protocol facade, or additional model-provider expansion is part of the active v1 roadmap unless the owner explicitly amends it.

## Post-v1 owner permission decision contract

The post-v1 roadmap adds a bounded owner permission-decision operation over the existing administration boundary. The model-facing runtime does not receive this operation. The operation binds an exact workflow continuation to its exact pending-permission identity and derives the standing-policy scope from durable controller-known metadata. `ALLOW_ONCE` and `ASK_EVERY_TIME` install `REQUIRE_APPROVAL`; exact approval remains bound to the fresh canonical request and is still re-evaluated before dispatch. `DENY_ONCE` is represented as an exact non-authorizing continuation closure rather than an aggregated pending-item resolution, so one owner denial cannot accidentally close another equivalent blocked request.

R1 supports only the exact trusted resource selector scope. R2 must make that selector/project identity session-project-aware before the TUI exposes `Always` choices as project-scoped UX. The accepted rc.11 authority, approval, emergency, continuation, sandbox, idempotency and fail-closed invariants remain unchanged.
