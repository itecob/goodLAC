# Build / Reuse / Adapt Matrix — Phase 0

This matrix preserves Phase 0 qualification history. It is not the active v1 roadmap; current roadmap authority is `PROJECT_STATE.json`, `tasks/ACTIVE_TASK.md`, the controlling specification as amended, and accepted ADRs.

| Component | Decision | Phase 0 disposition |
|---|---|---|
| Airlock | REUSE + WRAP | `AIRLOCK_WRAPPED`: consume upstream for Lane A compatibility; do not trust its HITL path as Lane B authority. |
| Preloop | REFERENCE/LAB | Broad control-plane comparison only; not v0.1 base. |
| agentgateway | DEFER | Historical optional protocol/data-plane candidate; no active v1 task. |
| Stonefold | REUSE IDEAS/TCK | Specification and conformance-test reference only; not trusted production runtime. |
| Waggle | IDEAS ONLY | No code reuse while authoritative license remains unresolved at the pinned revision. |
| OpenClaw | REFERENCE ONLY | Historical Phase 0 security/reference qualification only; no active v1 integration task. |
| Pi | REUSE / V1 REFERENCE | Sole reference harness for the active v1 roadmap; governed mode uses controller-backed tools only and a qualified LAC launch/profile. |
| FreeToken | REUSE EXTERNAL | Initial local inference endpoint; not part of authority path. |
| Cedar | DEFER | Candidate long-term `PolicyDecisionProvider`; no active v1 requirement. |
| OPA | DEFER | Candidate `PolicyDecisionProvider`; no active v1 requirement. |
| SQLite | REUSE LIBRARY | Canonical local state store in WAL mode. |
| Linux sandbox | REUSE QUALIFIED BACKEND | Rootless qualified sandbox boundary; do not build a custom sandbox without a concrete requirement. |
| LAC Authority Core | BUILD MISSING DELTA | Typed effects, canonicalization, exact approval binding, pre-dispatch recheck, leases, idempotency, emergency pause, durable receipts/audit. |
