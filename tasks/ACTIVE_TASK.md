# Active Task

**Task ID:** LAC-P0-REVIEW

**Objective:** Fresh independent read-only review of the Phase 0 upstream qualification candidate against the controlling specification and invariants.

**In scope:** pinned revision/license evidence, Airlock trace and ADR-001, secondary dispositions, deterministic Phase 0 evidence, package/install reproducibility.

**Out of scope:** implementation mutation; Phase 1 code; redesign; future-phase features.

**Required inputs:** `PROJECT_STATE.json`, `docs/ARCHITECTURE.md`, `UPSTREAM_LOCK.json`, `tasks/ACTIVE_TASK.md`, then Phase 0 qualification/ADR/evidence files as required.

**Required outputs:** `PASS` or `BLOCKED`, with findings classified only as `BLOCKER` or `NONBLOCKING`.

**Acceptance tests:** identify a concrete violated invariant/acceptance criterion/security boundary/required functionality/package/data-integrity/license requirement for any BLOCKER.

**Package required?** no

**Next task on success:** `LAC-C001` in Phase 1.
