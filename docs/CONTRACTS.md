# Contracts

## Canonical effect lifecycle

`PROPOSED -> EVALUATING -> {DENIED | PENDING_APPROVAL | AUTHORIZED}`

`PENDING_APPROVAL -> {REJECTED | APPROVED}`

`APPROVED -> AUTHORIZED` only after current-policy re-evaluation.

`AUTHORIZED -> LEASED -> EXECUTING -> {SUCCEEDED | FAILED}`

Additional terminal states: `CANCELLED`, `EXPIRED`, `REVOKED`.

## Effect request

Versioned `lac.effect-request/v1` with request/run/principal/agent identity, action, resource, typed arguments, idempotency key, timestamps, expiry, and canonical SHA-256.

## Policy decision

Versioned `lac.policy-decision/v1` bound to request ID and canonical request hash, with policy revision and deterministic reason codes.

## Approval

Versioned `lac.approval/v1`, bound to the exact canonical request hash and approver. `ONCE` is the initial scope; expiry and consumption are durable.

## Receipt

Versioned `lac.effect-receipt/v1`, bound to request, adapter, input hash, outcome, result hash, timing, and upstream reference where applicable.

## Execution lease

Short-lived, transactional single-machine ownership record keyed by request to prevent concurrent duplicate dispatch and support crash reconciliation.
