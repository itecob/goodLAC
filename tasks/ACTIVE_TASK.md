# Active Task

**Task ID:** `LAC-H004`

**Objective:** Complete the Phase 2 local-host-enforcement bypass/adversarial suite against the accepted H001 sandbox, H002 filesystem adapter, and H003 shell adapter; correct only concrete in-scope defects; and produce the Phase 2 candidate for fresh independent review.

**In scope:** deterministic actual-effect challenges for parent traversal; symlink escape; reads of `~/.ssh` and out-of-workspace `.env`; writes outside the configured workspace; denied deletion; unauthorized binary execution; shell launch through an otherwise allowed command; interpreter-based command escape; subprocess network access; inherited secret environment; and child processes attempting to outlive the sandbox; preservation of exact H003 executable/argv/cwd/environment binding; preservation of H002/H001 and the applicable Phase 1 authority gates; bounded remediation of defects exposed by these tests; Phase 2 candidate state and review handoff.

**Out of scope:** Pi or FreeToken integration; Phase 3 implementation; credentials/secret-provider implementation; Gmail, Calendar, Slack, Git, deployment, package/service or other external effects; production credentials; productization; architecture redesign absent a concrete violated binding requirement.

**Required inputs:** accepted Phase 1 authority core; H001 `qualification/evidence/h001_sandbox.json`; `decisions/ADR-004_SANDBOX_BACKEND.md`; H002 `filesystem:v1`; H003 `shell:v1`; controlling specification and Phase 2 invariants.

**Required outputs:** one complete H004 adversarial/conformance gate covering the binding Phase 2 bypass vectors as actual effects; any narrowly required H001/H002/H003 corrections with deterministic regression tests; passing `scripts/test-h003`, `scripts/test-h002`, `scripts/test-h001`, and applicable Phase 1 regression; Phase 2 candidate durable state; one owner-executable package whose successful execution hands the candidate to a fresh independent Phase 2 reviewer.

**Acceptance tests:** forbidden host effects are technically unavailable rather than merely policy-denied; arbitrary host paths and symlink escapes remain unavailable; generic shell cannot reach host credentials, arbitrary network, privilege escalation, nested shells/interpreters, or unbounded child processes; allowed bounded workspace effects remain functional; current policy/approval/lease/pause/idempotency/receipt authority remains mandatory; no Phase 3 capability is introduced.

**Package required?** yes

**Next task on success:** fresh `PHASE_BOUNDARY_INDEPENDENT_REVIEW` of the Phase 2 candidate. Do not begin Phase 3 before that review passes.
