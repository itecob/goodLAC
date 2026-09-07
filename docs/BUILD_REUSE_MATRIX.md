# Build / Reuse / Adapt Matrix — Phase 0

| Component | Decision | Phase 0 disposition |
|---|---|---|
| Airlock | REUSE + WRAP | `AIRLOCK_WRAPPED`: consume upstream for Lane A compatibility; do not trust its HITL path as Lane B authority. |
| Preloop | REFERENCE/LAB | Broad control-plane comparison only; not v0.1 base. |
| agentgateway | DEFER | Optional future protocol/data-plane gateway; do not stack it into v0.1 without a concrete requirement. |
| Stonefold | REUSE IDEAS/TCK | Specification and conformance-test reference only; not trusted production runtime. |
| Waggle | IDEAS ONLY | No code reuse while authoritative license remains unresolved at the pinned revision. |
| OpenClaw | ADAPT LATER | Phase 5 integration target and exact-execution-binding reference. |
| Pi | REUSE | Phase 3 initial harness; construct with controller-backed tools only. |
| FreeToken | REUSE EXTERNAL | Phase 3 initial local inference endpoint; not part of authority path. |
| Cedar | DEFER | Candidate long-term `PolicyDecisionProvider`; do not force into walking skeleton. |
| OPA | DEFER | Candidate `PolicyDecisionProvider`; no v0.1 requirement. |
| SQLite | REUSE LIBRARY | Phase 1 canonical local state store in WAL mode. |
| Linux sandbox | QUALIFY IN PHASE 2 | Rootless Podman and bubblewrap; do not build a custom sandbox. |
| LAC Authority Core | BUILD MISSING DELTA | Typed effects, canonicalization, exact approval binding, pre-dispatch recheck, leases, idempotency, emergency pause, durable receipts/audit. |
