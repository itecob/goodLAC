# Active Task

**Task ID:** LAC-C007

**Objective:** Implement the deterministic dispatcher authority boundary for canonical effect requests so an adapter invocation can occur only after immediate current-policy re-evaluation, any required exact one-time approval qualification, and successful acquisition of a current execution lease.

**In scope:** dispatcher/adapter boundary contract; immediate pre-dispatch policy re-evaluation (`INV-006`) against the current canonical request; durable recording of that policy decision using the existing policy-decision model; fail-closed handling of `DENY`; exact C005 approval validation for `REQUIRE_APPROVAL`; deterministic one-time approval consumption at the dispatch transition where required; C006 execution-lease acquisition after the final authority checks and before adapter invocation; deterministic ordering tests using an injected test double only; restart-safe durable state changes required by the dispatcher gate; deterministic C007 tests and applicable C001-C006 regressions.

**Out of scope:** a production simulated effect adapter (`LAC-C008`); real filesystem/shell/network/email/calendar or other external effects; emergency pause (`LAC-C009`); receipt/audit expansion (`LAC-C010`) beyond state required for the dispatcher gate; sandboxing; credentials; model/harness integration; external services; distributed execution; broad idempotency/reconciliation semantics not required for the C007 dispatch transition.

**Required inputs:** `PROJECT_STATE.json`, `docs/ARCHITECTURE.md`, `docs/CONTRACTS.md`, controlling specification, C002 canonical effect request, C003 policy decision provider/repository, C004 durable approval state, C005 exact approval-binding validator, C006 durable execution lease, and deterministic C001-C006 tests.

**Required outputs:** deterministic dispatcher boundary and adapter protocol/test-double contract; immediate pre-dispatch current-policy gate; approval-consumption transition where required; lease-before-adapter ordering; deterministic C007 tests; schema migration must be migration-tested if C007 requires one.

**Acceptance tests:** current policy is re-evaluated immediately before adapter invocation; a current `DENY` never reaches the adapter; `REQUIRE_APPROVAL` cannot reach the adapter without an unexpired unconsumed exact C005 approval; qualifying one-time approval cannot be reused after the dispatch transition; an execution lease is acquired only after authority checks and before adapter invocation; competing lease ownership prevents adapter invocation; malformed/unknown policy, approval, request, lease, or adapter state fails closed; no concrete external effect adapter or external service is introduced by C007.

**Package required?** no

**Next task on success:** `LAC-C008` simulated effect adapter.
