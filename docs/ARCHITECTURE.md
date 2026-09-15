# Architecture — Controlling Baseline v0.1

This file is the concise operating architecture derived from the controlling Technical Design and Implementation Specification v0.1 and the accepted Phase 4 permission-management amendment. It does not broaden the product into an assistant or workflow engine.

## Central rule

The AI proposes. Deterministic software authorizes and permits effects.

## Product separation

Local Agent Controller is an independent reusable authority/effect-control product. Chief of Staff, Omarchy Agent OS, Pi/OpenClaw agents, and future applications are consumers of LAC rather than components that own its authority semantics.

LAC may contain generic service effect adapters. It must not contain Chief of Staff workflow, memory, prioritization, briefing, meeting-preparation, follow-up, or other application business logic.

## Local-first contract

Canonical controller state, capability registry, pending-permission records, policy, identity, effect lifecycle, approvals, leases, audit, receipts, emergency pause, credential references, execution boundaries, and local model routing configuration remain local. Remote systems may be effect destinations but are not required for controller governance.

## Two lanes

**Lane A — compatibility governance:** existing MCP/tool calls may pass through Airlock with allow/ask/deny. This is lower assurance.

**Lane B — typed governed effects:** consequential operations enter the LAC Authority Core as versioned typed effect requests, are canonicalized, authenticated, capability-validated, policy-evaluated, approval-bound when required, re-evaluated immediately before dispatch, leased, and executed by bounded effect adapters.

## Runtime versus administration surfaces

LAC exposes logically separate control surfaces:

- **Runtime surface:** external applications submit governed requests and inspect permitted request/result state. Runtime consumers cannot mutate capability registration, standing policy, administrator identity, or controller invariants.
- **Administration surface:** the human owner manages capability registration, pending permission requests, standing policy, revocation, and exact approvals. v0.1 uses a separate owner-only Linux Unix-domain admin socket with peer-UID verification and no exposure inside governed agent sandboxes.

The first authoritative administration client is `lacctl`. Future TUI/web clients must consume the same admin API and never become canonical state writers.

## Permission-management contract

Capability registration, standing permission, and exact effect approval are distinct.

- Registration describes what a skill/application may request and grants zero authority.
- Standing policy returns only `ALLOW`, `REQUIRE_APPROVAL`, or `DENY`. User-facing `ASK` maps to `REQUIRE_APPROVAL`.
- Exact approval binds one canonical operation when required.
- Unknown/new capability, resource scope, or material argument shape is terminally denied and recorded in a bounded pending-permission queue. Resolving the queue item changes only future policy; the denied effect never resumes.

Conditional “allow unless / ask when” behavior is implemented through deterministic rules over trusted capability/resource/request metadata, never through model judgment.

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

## Required internal interfaces

`AgentAdapter`, `ModelProvider`, `PolicyDecisionProvider`, `ApprovalSurface`, `EffectAdapter`, `SandboxBackend`, `SecretProvider`, `AuditSink`, `StateStore`, plus the Phase 4 `CapabilityRegistry` and isolated administration surface.

## State and execution

SQLite WAL remains the single-machine durable store. An approval never transitions directly to execution; it must pass pre-dispatch policy re-evaluation and then a short-lived transactional execution lease. Permission/registry mutations are atomic, revisioned, auditable controller state and cannot mutate terminal effects.

## Sandbox and credentials

Governed tools alone are insufficient. The agent process must have bounded ambient filesystem/process/network/environment authority using an established Linux sandbox. Agents receive credential references, not credentials. Governed agent sandboxes must not expose the administration socket.

## Current Phase 4 sequence

`P001 -> P002 -> P003 -> P004 -> P005 -> P006 -> B002 -> B003 -> Phase 4 independent review`.

B001 Gmail remains accepted as a generic adapter precursor. The prior unexecuted B002 owner package is superseded. Chief of Staff begins only afterward as separate software.
