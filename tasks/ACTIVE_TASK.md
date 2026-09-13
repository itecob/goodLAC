# Active Task

**Task ID:** `LAC-P2-REVIEW`

**Objective:** Independently determine whether the complete Phase 2 local-host-enforcement candidate satisfies its binding acceptance criteria and controller invariants, including actual-effect bypass resistance across the H001 sandbox, H002 filesystem adapter, H003 shell adapter, and H004 adversarial suite.

**In scope:** verify candidate Git identity and clean state; verify the H004 implementation-to-handoff delta; read binding Phase 2 acceptance criteria/invariants; inspect H001 qualification evidence, H002/H003 implementation and tests, H004 remediation and actual-effect tests; run/challenge `scripts/test-h004`, `scripts/test-h003`, `scripts/test-h002`, `scripts/test-h001`, the applicable Phase 1 regression gates, and targeted additional read-only/reproducible tests needed to assess material claims; classify findings only as `BLOCKER` or `NONBLOCKING`; return exactly `PASS` or `BLOCKED` as the formal result.

**Out of scope:** implementation or remediation; Phase 3 implementation; Pi or FreeToken integration; credentials/secret-provider implementation; Gmail, Calendar, Slack, Git, deployment, package/service or other external effects; architecture redesign absent a demonstrated binding violation.

**Required inputs:** controlling specification; `PROJECT_STATE.json`; `docs/ARCHITECTURE.md`; `UPSTREAM_LOCK.json`; H001 qualification evidence and ADR-004; H002/H003 adapters/contracts/tests; H004 adversarial suite and candidate commit; accepted Phase 1 authority core and its preserved review identity.

**Required outputs:** one independent Phase 2 verdict of `PASS` or `BLOCKED`; concrete blocker IDs for every blocking finding, if any; nonblocking findings clearly separated; if `PASS`, a complete fresh implementation-segment successor prompt for `LAC-A001`; if `BLOCKED`, a complete fresh remediation-segment successor prompt limited to the blocker IDs.

**Acceptance tests:** every required Phase 2 forbidden effect is technically unavailable as an actual effect rather than merely policy-denied; workspace-bounded allowed effects remain functional; H001 network/environment/process containment remains effective; H002 path/symlink/deletion boundaries remain effective; H003 exact executable/argv/cwd/environment binding and H004 executable-class closure remain effective; Phase 1 policy/approval/lease/pause/idempotency/receipt authority remains mandatory; no Phase 3 capability is present.

**Package required?** no

**Next task on success:** `LAC-A001` in a fresh implementation session. Do not implement it during this review.
