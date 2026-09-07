# Architecture — Controlling Baseline v0.1

This file is the concise operating architecture derived from the controlling Technical Design and Implementation Specification v0.1. It does not broaden or replace that specification.

## Central rule

The AI proposes. Deterministic software authorizes and permits effects.

## Local-first contract

Canonical controller state, policy, identity, effect lifecycle, approvals, leases, audit, receipts, emergency pause, credential references, execution boundaries, and local model routing configuration remain local. Remote systems may be effect destinations but are not required for controller governance.

## Two lanes

**Lane A — compatibility governance:** existing MCP/tool calls may pass through Airlock with allow/ask/deny. This is lower assurance.

**Lane B — typed governed effects:** consequential operations enter the LAC Authority Core as versioned typed effect requests, are canonicalized, authenticated, policy-evaluated, approval-bound when required, re-evaluated immediately before dispatch, leased, and executed by bounded effect adapters.

## Binding invariants

- INV-001 no implicit authority.
- INV-002 model output is never authorization.
- INV-003 governed mode has no alternate consequential-effect bypass.
- INV-004 service credentials do not enter agent context.
- INV-005 approval binds the exact canonical security-relevant operation; security-relevant mutation invalidates approval.
- INV-006 policy is re-evaluated immediately before dispatch.
- INV-007 deny wins: `DENY > REQUIRE_APPROVAL > ALLOW` in v0.1.
- INV-008 consequential effects are idempotent where possible; controller prevents duplicates otherwise.
- INV-009 controller durable state is operational truth.
- INV-010 unknown state/action/adapter/resource/principal/approval/execution fails closed.
- INV-011 local emergency pause blocks new consequential effects without erasing inspection state.
- INV-012 audit never grants authority.
- INV-013 raw compatibility governance is explicitly lower assurance than typed effects.
- INV-014 deterministic work stays deterministic after typed intent translation.

## Required internal interfaces

`AgentAdapter`, `ModelProvider`, `PolicyDecisionProvider`, `ApprovalSurface`, `EffectAdapter`, `SandboxBackend`, `SecretProvider`, `AuditSink`, `StateStore`.

## State and execution

Phase 1 uses SQLite WAL on one machine. An approval never transitions directly to execution; it must pass pre-dispatch policy re-evaluation and then a short-lived transactional execution lease.

## Sandbox and credentials

Governed tools alone are insufficient. The agent process must have bounded ambient filesystem/process/network/environment authority using an established Linux sandbox. Agents receive credential references, not credentials.

## Scope discipline

Do not implement Phase 1+ features during Phase 0. Future ideas go to backlog only when concrete; they do not alter the active task.
