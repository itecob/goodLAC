# Active Task

**Task ID:** LAC-C004

**Objective:** Implement durable approval state for exact canonical effect requests after a `REQUIRE_APPROVAL` policy decision, without introducing execution or dispatch.

**In scope:** versioned `lac.approval/v1`; approval ID/request ID/canonical request hash/approver/decision/scope/timestamps; initial `ONCE` scope; durable approval persistence; explicit APPROVE/REJECT decision state; expiry representation and deterministic validation; binding to an existing canonical request and qualifying policy decision; immutable decision identity; restart persistence.

**Out of scope:** post-approval exact-binding enforcement and mutation rejection logic beyond durable record binding (`LAC-C005`), execution leases, dispatch, simulated or real effects, emergency pause, receipts/audit semantics beyond persistence required by this task, host adapters, sandboxing, credentials, model/harness integration, and external services.

**Required inputs:** `PROJECT_STATE.json`, `docs/ARCHITECTURE.md`, `docs/CONTRACTS.md`, controlling specification, C001 StateStore, C002 canonical effect request, C003 policy-decision provider/persistence, and deterministic C001-C003 tests.

**Required outputs:** approval domain/state implementation, required state-store migration/persistence, and deterministic C004 tests.

**Acceptance tests:** approval is versioned and binds request ID plus canonical request hash; only a durable `REQUIRE_APPROVAL` decision for the same request/hash can support approval creation; malformed/unknown approval decision or scope fails closed; expiry is durable and validated; approval state survives restart; duplicate approval identity cannot silently overwrite different material; no approval record directly executes or authorizes dispatch.

**Package required?** no

**Next task on success:** `LAC-C005` exact approval binding.
