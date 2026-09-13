# Active Task

**Task ID:** `LAC-H002`

**Objective:** Implement the Phase 2 typed filesystem effect adapter on top of the accepted Phase 1 authority core and the H001-qualified `SandboxBackend`, establishing a bounded working-root filesystem effect path whose forbidden host effects are technically unavailable.

**In scope:** typed filesystem effect operations required for the first governed local workspace; canonical path handling; bounded working-root enforcement; read/write semantics needed by the controlling specification; symlink and traversal resistance; deterministic adapter integration with the existing dispatcher/lease/receipt path; sandbox use where required to prevent alternate ambient host access; H002-specific unit/integration/adversarial tests; applicable documentation only when needed to describe the filesystem contract.

**Out of scope:** `LAC-H003` shell effect adapter; complete `LAC-H004` bypass suite; Pi/FreeToken integration; credentials/secret-provider implementation; Gmail, Calendar, Slack, Git, deployment, package/service effects; production credentials; architecture redesign absent a concrete violated binding requirement.

**Required inputs:** accepted Phase 1 authority core; `qualification/evidence/h001_sandbox.json`; `decisions/ADR-004_SANDBOX_BACKEND.md`; `packages/sandbox/`; controlling specification and Phase 2 invariants.

**Required outputs:** one bounded filesystem `EffectAdapter` implementation; deterministic H002 tests proving allowed workspace operations succeed and path traversal/symlink/out-of-root effects fail before host mutation; applicable Phase 1 regression remains passing; one owner-executable H002 package; durable transition to `LAC-H003` only after successful owner execution.

**Acceptance tests:** allowed bounded read/write behavior is deterministic; paths outside the configured working root are unavailable; `..` traversal fails; symlink escape fails; denied deletion cannot occur; unknown/malformed filesystem operations fail closed; adapter invocation remains behind Phase 1 policy/approval/lease/pause/idempotency authority; sandbox qualification remains valid; no shell adapter or future-phase capability is introduced.

**Package required?** yes

**Next task on success:** `LAC-H003` — shell effect adapter. Do not implement it in the H002 session.
