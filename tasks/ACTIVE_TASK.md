# Active Task

**Task ID:** LAC-C001

**Objective:** Establish the Phase 1 durable local state-store foundation using SQLite in WAL mode.

**In scope:** the `StateStore` internal interface; SQLite database creation/configuration; forward-only schema migration registry with integrity checks; transactional primitives; minimal durable `system_state`; restart persistence; fail-closed handling of unsupported or inconsistent schema state; deterministic C001 tests.

**Out of scope:** canonical effect-request semantics, policy decisions, approvals, approval binding, execution leases, dispatcher behavior, simulated effects, emergency pause behavior, receipts/audit semantics, host adapters, sandboxing, model or harness integration, credentials, and external effects.

**Required inputs:** `PROJECT_STATE.json`, `docs/ARCHITECTURE.md`, `docs/CONTRACTS.md`, `docs/TEST_STRATEGY.md`, `docs/TECHNICAL_DESIGN_AND_IMPLEMENTATION_SPECIFICATION_v0.1.md`, and the Phase 0 PASS handoff.

**Required outputs:** `packages/state/`, `tests/unit/test_state_store.py`, and `scripts/test-c001`.

**Acceptance tests:** new state databases use SQLite WAL with foreign keys enabled; supported schema initializes deterministically; durable state survives close/reopen; failed transactions roll back; unsupported future schema and migration-integrity mismatch fail closed; database file permissions are owner-only on POSIX; no external service, credential, or consequential effect is introduced.

**Package required?** no

**Next task on success:** `LAC-C002` canonical effect request.
