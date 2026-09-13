# Active Task

**Task ID:** `LAC-P1-REVIEW`

**Objective:** Perform one fresh, independent, read-only Phase 1 re-review of the corrected controller walking-skeleton candidate after remediation of `LAC-P1-B001` and `LAC-P1-B002`, and return exactly `PASS` or `BLOCKED` against the binding Phase 1 specification, invariants, and deterministic evidence.

**In scope:** corrected candidate Git identity and clean-state verification; explicit re-test of fresh request/lease authority immediately before new adapter invocation; LEASED recovery freshness; no false success or retry revival after pre-invocation expiry; durable agent active/revoked identity state and principal binding; permanent `revoked agent cannot act` acceptance coverage; complete C001-C010 behavior and migrations; canonical request/policy/approval/lease/dispatcher ordering; simulated adapter; emergency pause; durable execution/receipts/audit; duplicate/restart reconciliation; Phase 1 deterministic tests; INV-001 through INV-014 as applicable to Phase 1; regression challenge of previously passing Phase 1 invariants.

**Out of scope:** remediation during review; Phase 2 filesystem/shell/package/service enforcement; sandbox implementation; real network/email/calendar/Slack/Git/deploy effects; credential brokering; model/harness integration; architecture redesign absent a concrete violated binding requirement.

**Required inputs:** the corrected Phase 1 candidate commit recorded in the root handoff prompt; owner remediation-package execution evidence; durable `PROJECT_STATE.json`; this task; controlling specification; corrected source/tests plus C001-C010 source/tests and migration state.

**Required outputs:** exactly one review judgment, `PASS` or `BLOCKED`; concrete blocker IDs only for violations meeting the project blocker standard; nonblocking observations kept separate; on PASS, a complete successor prompt for fresh Phase 2 `LAC-H001`; on BLOCKED, a complete fresh remediation-segment prompt limited to blocker IDs.

**Acceptance:** independently verify both prior blockers are actually closed and that remediation did not regress the Phase 1 authority lifecycle: request/lease authority is fresh at invocation start; revoked agents cannot reach simulated invocation; unknown agents still fail closed; deny/approval/exact binding/pre-dispatch recheck/lease/pause remain authoritative; duplicate governed simulated effects execute at most once or reconcile safely; crash windows cannot create false terminal success; success/failure receipts are durable and verifiably bound with truthful timing; audit is append-oriented and never grants authority; restart behavior is safe; applicable deterministic gates pass; no Phase 2 capability was introduced.

**Next task on PASS:** `LAC-H001` — begin Phase 2 with sandbox-backend qualification/implementation as defined by the controlling specification. Do not implement it in the review session.
