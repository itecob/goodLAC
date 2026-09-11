# Active Task

**Task ID:** LAC-C005

**Objective:** Implement deterministic exact post-approval binding validation so an approval can qualify only the same canonical effect request it was issued for, with mutation, rejection, expiry, or prior consumption failing closed, without introducing execution leases or dispatch.

**In scope:** validate a durable `lac.approval/v1` against the current canonical `lac.effect-request/v1`; exact request ID and canonical-request-hash equality; only `APPROVE` with initial `ONCE` scope; deterministic expiry check at an explicit supplied time; reject already-consumed approval state; reject any security-relevant request mutation through canonical hash mismatch; preserve binding to the qualifying durable `REQUIRE_APPROVAL` policy decision; deterministic C005 tests across all C002 security-relevant request fields.

**Out of scope:** current-policy pre-dispatch re-evaluation (`INV-006`), changing/consuming approval state as part of execution, execution leases (`LAC-C006`), dispatch, simulated or real effects, emergency pause, receipts/audit semantics beyond existing persistence, sandboxing, credentials, model/harness integration, and external services.

**Required inputs:** `PROJECT_STATE.json`, `docs/ARCHITECTURE.md`, `docs/CONTRACTS.md`, controlling specification, C002 canonical effect request, C003 durable policy decision, C004 durable approval state, and deterministic C001-C004 tests.

**Required outputs:** exact approval-binding validator/service and deterministic C005 tests; any persistence change must be strictly required by the validator and migration-tested.

**Acceptance tests:** the exact unchanged canonical request can satisfy binding with a current unconsumed `APPROVE`/`ONCE` approval; `REJECT`, expired, consumed, unknown/malformed approval, wrong request ID, wrong canonical hash, or lost qualifying policy-decision binding fails closed; mutation of arguments, target/resource, principal, agent, action, run, idempotency key, or request timing invalidates the prior approval via canonical-hash mismatch; validation alone cannot lease, dispatch, or execute an effect.

**Package required?** no

**Next task on success:** `LAC-C006` execution lease.
