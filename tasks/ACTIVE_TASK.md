# Active Task

**Task ID:** LAC-C002

**Objective:** Implement the canonical versioned effect request and deterministic canonical request hash on the C001 durable StateStore foundation.

**In scope:** `lac.effect-request/v1`; request/run/principal/agent identity; action; resource; typed JSON arguments; idempotency key; creation/expiry timestamps; deterministic canonicalization and SHA-256; validation; durable persistence needed for the effect request.

**Out of scope:** policy decisions, approvals, approval binding, execution leases, dispatch, simulated or real effects, emergency pause, receipts/audit semantics beyond persistence required by this task, sandboxing, credentials, model/harness integration, and external services.

**Required inputs:** `PROJECT_STATE.json`, `docs/ARCHITECTURE.md`, `docs/CONTRACTS.md`, `docs/TECHNICAL_DESIGN_AND_IMPLEMENTATION_SPECIFICATION_v0.1.md`, `packages/state/`, and C001 deterministic test results.

**Required outputs:** canonical effect-request implementation, required state-store migration/persistence, and deterministic C002 tests.

**Acceptance tests:** identical semantic requests canonicalize identically regardless of JSON object key order; every security-relevant field participates in the canonical hash; changing a security-relevant field changes the hash; malformed/unknown required fields fail closed; non-canonical JSON values are rejected; persisted requests survive restart; duplicate request identity cannot silently overwrite a different canonical request.

**Package required?** no

**Next task on success:** `LAC-C003` policy interface.
