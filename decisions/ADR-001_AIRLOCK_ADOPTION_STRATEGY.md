# ADR-001 — Airlock Adoption Strategy

- **Status:** Accepted as Phase 0 candidate; subject to one independent phase-boundary review
- **Decision:** `AIRLOCK_WRAPPED`
- **Pinned source:** `airlock-dev/airlock@68a71c7f0139c823971b95a79cf800e837630d3a`

## Context

LAC requires both a lower-assurance compatibility lane and a stronger typed-effect authority lane. The default adoption order is upstream -> wrapper -> minimal patch -> derivative -> reject.

## Source finding

Airlock's fixed middleware chain evaluates policy before the HITL gate and then proceeds from an approved HITL result to execution. The HITL approval is created from redacted arguments while the live original call context is retained for downstream execution. The pinned path does not establish a LAC-style canonical request hash binding and does not re-evaluate policy immediately before dispatch.

Airlock's HITL engine nevertheless persists pending approval records, applies timeout state, consumes pending approvals, and recovers pending rows after restart. Those capabilities remain useful for compatibility governance.

## Decision

Consume stock Airlock as an upstream Lane A compatibility gateway behind a LAC adapter boundary. Do not fork it. Do not make Airlock approval state canonical for consequential typed effects.

Build the missing Lane B authority core as the narrow LAC-owned delta: typed request canonicalization, exact approval binding, current-policy pre-dispatch recheck, execution leases, idempotency/duplicate prevention, emergency pause, durable receipts and canonical state.

## Why not other dispositions

- `AIRLOCK_UPSTREAM`: rejected for Lane B because INV-005/006 are not satisfied by the pinned HITL path.
- `AIRLOCK_MINIMAL_PATCH`: unnecessary; patch ownership would enlarge maintenance burden when a clean boundary can keep upstream unmodified.
- `AIRLOCK_DERIVATIVE`: unnecessary and contrary to reuse-first policy.
- `AIRLOCK_REJECTED`: too strong; Airlock remains useful for Lane A.

## Consequences

Airlock is replaceable and non-canonical. Phase 1 does not depend on Airlock internals for typed effects. Future Airlock upgrades must be re-qualified before changing the pin.
