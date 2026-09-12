# Active Task

**Task ID:** `LAC-P1-REVIEW`

**Objective:** Perform one fresh, independent, read-only Phase 1 boundary review of the completed C001-C010 controller walking-skeleton candidate and return exactly `PASS` or `BLOCKED` against the binding Phase 1 specification, invariants, and deterministic evidence.

**In scope:** candidate Git identity and clean-state verification; complete C001-C010 implementation and migration evidence; canonical request/policy/approval/lease/dispatcher ordering; simulated adapter; emergency pause; durable execution/receipts/audit; duplicate/restart reconciliation; Phase 1 deterministic tests; INV-001 through INV-014 as applicable to Phase 1; Phase 1 demonstration and permanent acceptance tests applicable before Phase 2.

**Out of scope:** remediation during review; Phase 2 filesystem/shell/package/service enforcement; sandbox implementation; real network/email/calendar/Slack/Git/deploy effects; credential brokering; model/harness integration; architecture redesign absent a concrete violated binding requirement.

**Required inputs:** the exact C010 implementation candidate commit recorded in the root handoff prompt; owner C010 package execution evidence; durable `PROJECT_STATE.json`; this task; controlling specification; C001-C010 source/tests and migration state.

**Required outputs:** exactly one review judgment, `PASS` or `BLOCKED`; concrete blocker IDs only for violations meeting the project blocker standard; nonblocking observations kept separate; on PASS, a complete successor prompt for fresh Phase 2 `LAC-H001`; on BLOCKED, a complete fresh remediation-segment prompt limited to blocker IDs.

**Acceptance:** independently verify that the candidate proves the Phase 1 authority lifecycle without real external effects; deny/approval/exact binding/pre-dispatch recheck/lease/pause remain authoritative; duplicate governed simulated effects execute at most once or reconcile safely; crash windows cannot create false terminal success; success/failure receipts are durable and verifiably bound; audit is append-oriented and never grants authority; restart/migration behavior is safe; applicable deterministic gates pass; no Phase 2 capability was introduced.

**Next task on PASS:** `LAC-H001` — begin Phase 2 with sandbox-backend qualification/implementation as defined by the controlling specification. Do not implement it in the review session.
