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

## H002 filesystem effect contract

The first governed workspace uses adapter `filesystem:v1` and one explicitly configured resource/root, normally `filesystem:workspace`. Paths are canonical relative POSIX paths; absolute paths, traversal, non-canonical aliases, control characters, and symlink traversal fail closed.

Typed actions are:

- `filesystem.read` with exactly `{path}` — read an existing UTF-8 regular file; the workspace is mounted read-only for the effect.
- `filesystem.create` with exactly `{path, content}` — create an absent UTF-8 text file beneath an existing real directory.
- `filesystem.replace` with exactly `{path, content}` — replace an existing UTF-8 regular non-symlink file. Policy can therefore require approval for overwrite independently of create.
- `filesystem.delete` with exactly `{path}` — recognized for deterministic policy denial, but H002 provides no deletion mutation implementation.

Read/create/replace execute through the H001-selected qualified `SandboxBackend`. The sandbox exposes only the configured workspace plus the fixed helper runtime/input required for the operation, with `network=none`, cleared environment, and no arbitrary host filesystem visibility. Mutating PREPARED executions are not guessed during reconciliation; only read reconciliation may be safely repeated.
