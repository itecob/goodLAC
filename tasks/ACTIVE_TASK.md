# Active Task

**Task ID:** LAC-C009

**Objective:** Implement the Phase 1 local emergency pause so new simulated effects cannot cross the C007/C008 dispatcher boundary while paused, without erasing or making existing controller state unavailable for read-only inspection.

**In scope:** one durable local emergency-pause state and narrow API; deterministic pause/resume semantics; dispatcher enforcement that fails closed on malformed/unreadable pause authority; restart survival; deterministic C009 tests; applicable C001-C008 regressions; schema migration only if demonstrably required.

**Out of scope:** receipt/audit expansion and broader duplicate-effect reconciliation (`LAC-C010`); filesystem/shell/network/email/calendar or other real external effects; sandboxing; credentials; model/harness integration; external services; distributed execution; production adapters.

**Required inputs:** `PROJECT_STATE.json`, `docs/ARCHITECTURE.md`, `docs/CONTRACTS.md`, controlling specification, C001 state store, C002 canonical effect request, C003 policy provider/repository, C004 approval state, C005 exact approval binding, C006 execution lease, C007 dispatcher, C008 deterministic simulated adapter, and deterministic C001-C008 tests.

**Required outputs:** durable emergency-pause state/API; dispatcher integration that prevents adapter invocation while paused; pause/resume behavior that preserves inspectable controller state; restart-safe deterministic tests and applicable regression evidence.

**Acceptance tests:** pause state is local and durable across restart; a paused controller prevents ALLOW and otherwise-qualifying approved simulated effects from invoking the adapter; pause does not erase canonical requests, approvals, policy decisions, leases, or other inspectable state; malformed/unreadable pause authority fails closed; resume does not itself execute anything and an expired or otherwise-invalid request remains unable to execute; existing DENY/exact-approval/lease ordering remains authoritative; C001-C008 regressions remain passing; no C010 or later capability is introduced.

**Package required?** yes

**Next task on success:** `LAC-C010` receipts/audit and duplicate-effect reconciliation.
