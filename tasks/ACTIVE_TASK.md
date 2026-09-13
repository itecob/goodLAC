# Active Task

**Task ID:** `LAC-H003`

**Objective:** Implement the Phase 2 typed shell effect adapter on top of the accepted Phase 1 authority core, H001-qualified `SandboxBackend`, and H002 bounded workspace, so governed command execution has exact typed argv/cwd/environment semantics and no ambient host/network/credential authority.

**In scope:** typed shell effect request(s) required for the first governed local workspace; exact argv/executable binding; canonical cwd constrained to the configured workspace; deterministic environment construction rather than inherited host environment; use of the selected sandbox backend; network disabled unless a later explicitly authorized task changes that contract; explicit fail-closed handling for unsupported executables/arguments/working directories; adapter integration behind the existing dispatcher/lease/receipt path; H003-specific unit/integration/adversarial tests; concise contract documentation where required.

**Out of scope:** complete `LAC-H004` bypass/conformance suite; Pi/FreeToken integration; credentials/secret-provider implementation; Gmail, Calendar, Slack, Git, deployment, package/service adapters; production credentials; architecture redesign absent a concrete violated binding requirement.

**Required inputs:** accepted Phase 1 authority core; H001 `qualification/evidence/h001_sandbox.json`; `decisions/ADR-004_SANDBOX_BACKEND.md`; H002 `packages/effects/filesystem/`; controlling specification and Phase 2 invariants.

**Required outputs:** one bounded shell `EffectAdapter`; exact typed execution semantics with no shell-string authority by default; deterministic H003 tests showing allowed bounded commands work while disallowed executable/cwd/environment/network/privilege paths fail before host effect; H001 and H002 gates preserved; applicable Phase 1 regression remains passing; one owner-executable H003 package; durable transition to `LAC-H004` only after successful owner execution.

**Acceptance tests:** exact argv/cwd/resource material is authority-bound; allowed bounded project commands execute inside the selected sandbox; arbitrary host cwd is unavailable; inherited secret environment is unavailable; outbound network remains unavailable; `sudo`/privilege escalation and unsupported executables fail closed; adapter invocation remains behind Phase 1 policy/approval/lease/pause/idempotency authority; filesystem and sandbox regressions remain passing; no H004 or later capability is introduced.

**Package required?** yes

**Next task on success:** `LAC-H004` — complete Phase 2 bypass/adversarial suite and phase candidate. Do not implement it in the H003 session.
