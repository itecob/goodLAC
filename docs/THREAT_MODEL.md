# Threat Model

## Protected assets

Host filesystem, process authority, service credentials, external accounts, canonical controller state, approvals, execution leases, effect receipts, and audit integrity.

## Primary adversarial conditions

- malicious or mistaken model output;
- prompt/tool-output injection;
- malformed or mutated tool arguments;
- harness retry/duplication;
- approval TOCTOU;
- alternate host-effect bypass;
- path/symlink/interpreter/subprocess escape;
- credential inheritance or leakage;
- restart/crash around dispatch;
- concurrent duplicate execution.

## Required controls

Typed canonical requests, exact approval binding, immediate pre-dispatch policy recheck, deny precedence, idempotency, execution leases, durable SQLite transactions, emergency pause, credential isolation, sandboxing, and adversarial tests that verify whether the real effect can occur rather than merely checking a policy return value.

## Phase 0 security question

Can Airlock be trusted for Lane B authorization semantics without modification? The pinned source inspection concludes no; ADR-001 limits it to a wrapped compatibility role while LAC owns Lane B authority.
