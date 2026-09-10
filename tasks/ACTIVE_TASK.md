# Active Task

**Task ID:** LAC-C003

**Objective:** Implement the deterministic `PolicyDecisionProvider` interface and initial local policy-decision semantics over canonical effect requests.

**In scope:** versioned policy-decision domain model; `PolicyDecisionProvider` internal interface; deterministic `ALLOW`, `REQUIRE_APPROVAL`, and `DENY` outcomes; deny precedence; binding each decision to request ID and canonical request hash; policy revision and deterministic reason codes; durable policy-decision persistence needed by this task; fail-closed treatment of unknown policy state/action/principal/agent/resource as required by the current policy provider.

**Out of scope:** approval records and approval surfaces, exact approval consumption, execution leases, dispatch, simulated or real effects, emergency pause, receipts/audit semantics beyond persistence required by this task, host adapters, sandboxing, credentials, model/harness integration, and external services.

**Required inputs:** `PROJECT_STATE.json`, `docs/ARCHITECTURE.md`, `docs/CONTRACTS.md`, `docs/TECHNICAL_DESIGN_AND_IMPLEMENTATION_SPECIFICATION_v0.1.md`, C001 StateStore, C002 canonical effect request, and deterministic C001/C002 tests.

**Required outputs:** policy-decision domain/interface implementation, required state-store migration/persistence, and deterministic C003 tests.

**Acceptance tests:** decisions bind request ID and canonical hash; explicit deny wins over weaker authority; approval-required cannot become allow through ambiguity; unknown or malformed policy state fails closed; deterministic inputs produce deterministic decisions and reason codes; policy decisions persist across restart without changing their request binding; no approval or dispatch behavior is introduced.

**Package required?** no

**Next task on success:** `LAC-C004` approval state.
