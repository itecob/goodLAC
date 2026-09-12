# Active Task

**Task ID:** LAC-C008

**Objective:** Implement the first concrete deterministic simulated effect adapter behind the C007 `EffectAdapter` boundary so the Phase 1 authority lifecycle can invoke a bounded non-consequential effect without introducing any real external effect capability.

**In scope:** one simulated adapter implementing the C007 adapter protocol; explicit supported simulated action/resource contract; deterministic simulated result/state sufficient to prove the adapter was invoked only after the C007 policy/approval/lease gate; fail-closed handling of unsupported or malformed simulated requests; deterministic C008 tests; applicable C001-C007 regressions; restart-safe state only if strictly required by the simulated adapter and already compatible with current Phase 1 scope.

**Out of scope:** filesystem/shell/network/email/calendar or any other real external effect; emergency pause (`LAC-C009`); receipt/audit expansion and broader duplicate-effect reconciliation (`LAC-C010`); sandboxing; credentials; model/harness integration; external services; distributed execution; production business adapters.

**Required inputs:** `PROJECT_STATE.json`, `docs/ARCHITECTURE.md`, `docs/CONTRACTS.md`, controlling specification, C002 canonical effect request, C003 policy provider/repository, C004 approval state, C005 exact approval binding, C006 execution lease, C007 dispatcher/adapter protocol, and deterministic C001-C007 tests.

**Required outputs:** one concrete deterministic simulated effect adapter; explicit narrow support contract; deterministic integration tests proving ALLOW and qualifying REQUIRE_APPROVAL paths can reach it only through the C007 dispatcher gate while DENY/invalid authority cannot; applicable regression evidence.

**Acceptance tests:** the adapter implements the C007 `EffectAdapter` protocol; it explicitly supports only its declared simulated request shape and fails closed otherwise; its invocation produces no filesystem, shell, network, email, calendar, credential, or other external effect; current `DENY` never invokes it; `REQUIRE_APPROVAL` reaches it only after exact one-time approval consumption and lease acquisition; deterministic simulated output is bound to the canonical request and lease used for invocation; C001-C007 regressions remain passing; no C009/C010 or later capability is introduced.

**Package required?** no

**Next task on success:** `LAC-C009` emergency pause.
