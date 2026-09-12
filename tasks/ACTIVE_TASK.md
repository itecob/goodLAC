# Active Task

**Task ID:** `LAC-C010`

**Objective:** Complete the Phase 1 walking skeleton by adding durable effect receipts/audit and duplicate-effect reconciliation for the governed simulated-effect path. The controller must be able to distinguish authorized-but-not-invoked, successful, failed, and safely reconcilable duplicate/restart cases without allowing audit data to grant authority.

**In scope:** versioned durable effect-receipt state; append-oriented audit events for material lifecycle transitions; receipt binding to request, adapter, canonical input, outcome/result, timing, and upstream reference where applicable; deterministic duplicate-effect prevention/reconciliation for the Phase 1 simulated adapter; restart/crash-window tests; required SQLite schema/data migration with rollback-safe verification; C001-C009 regression tests; preparation of the Phase 1 candidate for one fresh independent review after successful owner execution.

**Out of scope:** Phase 2 filesystem/shell/package/service enforcement; real network/email/calendar/Slack/Git/deploy effects; credential brokering; sandbox/OS confinement; model or harness integration; cloud/SaaS requirements; optional policy-engine replacement; broader production reconciliation beyond the Phase 1 simulated-effect acceptance surface.

**Required inputs:** accepted C001-C009 implementation, especially canonical `EffectRequest`, deterministic policy decisions, exact one-time approvals, execution leases, dispatcher ordering, the C008 simulated adapter, and the C009 durable emergency pause; controlling specification receipt/audit/idempotency/restart requirements; INV-008, INV-009, INV-011, INV-012, and INV-013.

**Required outputs:** versioned durable receipt/audit schema and repositories; deterministic dispatcher/adapter reconciliation semantics that do not duplicate the simulated effect; verifiable success/failure receipts; append-oriented audit evidence consistent with canonical state; migration and restart coverage; deterministic C010 tests plus all applicable C001-C009 regressions.

**Acceptance:** duplicate dispatch of the same governed effect does not produce a second simulated effect; crash before adapter invocation cannot produce a false-success receipt; the authorized/leased-to-invocation crash window is durably distinguishable and reconcilable without treating audit as authority; adapter failure has a durable failure outcome/receipt; successful effect has a verifiable receipt bound to the canonical request/adapter/result; restart preserves terminal effect/receipt/audit state; emergency pause remains authoritative and does not erase state; malformed/unknown reconciliation state fails closed; C001-C009 regressions remain green; no Phase 2 capability is introduced.

**Next task on success:** `LAC-P1-REVIEW` — one fresh independent read-only Phase 1 boundary review of the completed walking-skeleton candidate. Do not begin Phase 2 before that review passes.
