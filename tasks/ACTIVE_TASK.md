# ACTIVE TASK — LAC-P002

## Task ID

`LAC-P002`

## Objective

Implement deterministic fail-closed handling for unknown/new capability material and a bounded durable pending-permission queue for administrator review, while guaranteeing that the denied effect is terminal and can never be resumed by later registry or policy changes.

## In scope

- Consume the accepted P001 canonical capability registry as trusted descriptive metadata; registration continues to grant zero authority.
- Add deterministic capability/request validation needed to classify unknown action, unknown resource type/selector/scope, unsupported capability/manifest version, and materially new argument shape before authority can progress.
- Terminally deny the current effect for unknown/new material before lease/adapter mutation and record a bounded pending-permission record for later administrator review.
- Define a versioned canonical pending-permission record with bounded/redacted metadata sufficient to identify requester/application/skill/action/resource/reason/material shape without persisting raw service credentials.
- Aggregate equivalent repeated unknown requests deterministically, preserving first-seen, last-seen, count, requester identity, capability identity/revision/version context, action/resource, reason, and bounded schema/shape metadata.
- Preserve closed-effect semantics: queue resolution is not implemented in P002 and no pending record is executable/resumable authority.
- Keep pending-permission mutation/inspection internal to controller code in P002; do not expose the future external admin socket/API or `lacctl`.
- Add deterministic unit/integration/negative-security tests and run the accepted regression gate including P001 and B001.

## Out of scope

- Scoped/conditional standing-policy evaluation or user policy editing (`LAC-P003`).
- Secure external admin API/socket or peer-UID authentication (`LAC-P004`).
- `lacctl` (`LAC-P005`).
- Permission-management E2E (`LAC-P006`).
- Calendar (`LAC-B002`), generic external-consumer proof (`LAC-B003`), Chief of Staff, OpenClaw, Omarchy Agent OS, web UI/TUI, enterprise RBAC, or model-authored policy.
- Resolving a pending-permission record into policy; that belongs to later permission-administration work.

## Required inputs

- Accepted P001 `packages/capabilities/` manifest/registry contract and `docs/CAPABILITY_MANIFEST_v1.md`.
- `docs/PERMISSION_MANAGEMENT.md` and `decisions/ADR-007_PERMISSION_ADMINISTRATION_AND_CAPABILITY_GOVERNANCE.md`.
- `docs/ARCHITECTURE.md`, `docs/CONTRACTS.md`, and Phase 4 binding invariants.
- Existing effect request, policy, dispatcher, state-store, receipt/audit, and terminal-state interfaces only as required to prove fail-closed behavior.

## Required outputs

- Versioned canonical pending-permission domain model and durable bounded/aggregating repository.
- Deterministic capability/request validation that terminally denies unknown/new material before lease or adapter mutation.
- Tests proving bounded aggregation, credential-safe metadata, terminal denial, non-resumability, and zero authority from queue state.
- Applicable accepted regression evidence including P001 and B001.
- One owner-executable package completing P002 and activating fresh `LAC-P003` on success.

## Acceptance tests

At minimum prove deterministically that:

1. unknown action is terminally denied and produces one pending-permission record with no lease or adapter mutation;
2. unknown resource type/selector/scope is terminally denied and queued;
3. unsupported capability/manifest version or materially new argument shape fails closed and is queued;
4. equivalent repeated unknown requests aggregate into one bounded record with deterministic count/first-seen/last-seen behavior rather than unbounded queue growth;
5. pending records contain no raw credential values or unbounded request payloads;
6. a pending-permission record is not an approval, policy decision granting authority, execution lease, or resumable effect;
7. registry/policy changes made after a denial cannot transition the original closed effect back toward execution;
8. no runtime/agent-facing P002 interface can administer registry, standing policy, or pending resolution;
9. P001 and applicable Phase 1–3/A004/B001 regressions remain passing.

## Package required?

Yes.

## Next task on success

`LAC-P003` in a fresh implementation session.
