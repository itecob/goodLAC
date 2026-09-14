# Active Task

**Task ID:** `LAC-A001`

**Mode / role:** `IMPLEMENTATION_SEGMENT` / **Lead Implementation Engineer**

**Objective:** Implement the first Pi `AgentAdapter` integration for Phase 3 so a Pi-based agent harness can expose only LAC controller-backed governed local tools while preserving the existing Authority Core and Phase 2 host boundary. This task integrates the harness boundary only; it does not integrate FreeToken or perform the full local-model E2E.

**In scope:** verify the preserved Phase 2 review; inspect the pinned Pi revision `da840b6216578c2a571d0374ac6a2091a83f9d91` and the qualified local checkout; implement the minimum Pi adapter/harness integration behind the `AgentAdapter` boundary; construct Pi with controller-backed tools only; map supported Pi tool requests into exact typed LAC effect requests without letting model output become authorization; route consequential filesystem/shell work through the existing Dispatcher/effect adapters/sandbox; add deterministic unit/integration/negative-conformance tests; run all applicable Phase 1 and Phase 2 regressions; prepare one owner-executable package that advances to `LAC-A002` only after A001 passes.

**Out of scope:** FreeToken installation/configuration; real local-model inference; `LAC-A002`; `LAC-A003`; OpenClaw; Gmail/Calendar; new authority semantics; new policy language; broadening the reviewed generic shell executable class; weakening or replacing the H001-H004 boundary; production credentials or external consequential effects.

**Required inputs:** reviewed Phase 2 candidate `aab830122d85b4fcb4f1b5cb7f62e8ba82a23803`; Phase 1 reviewed commit `ba21d50c26540147c458a8e3f402e15e71efe9c7`; selected H001 backend `bubblewrap`; `filesystem:v1`; `shell:v1`; pinned Pi upstream `earendil-works/pi@da840b6216578c2a571d0374ac6a2091a83f9d91`; `UPSTREAM_LOCK.json`; `docs/TECHNICAL_DESIGN_AND_IMPLEMENTATION_SPECIFICATION_v0.1.md`; `docs/CONTRACTS.md`; Phase 1/2 deterministic gates.

**Required outputs:** a bounded Pi adapter/harness integration under the established adapter boundary; deterministic tests proving the exposed Pi tool surface is controller-backed and cannot silently fall back to unrestricted default Pi filesystem/process tools; any minimal dependency/provenance updates actually required by implementation; one owner package completing A001 and installing the fresh `LAC-A002` successor prompt.

**Acceptance tests:** Pi is constructed with only the intended LAC-backed tool surface; no stock unrestricted Bash/read/edit/write path is exposed in governed mode; supported tool calls become exact canonical LAC requests and execute only through existing deterministic authorization/dispatch/sandbox paths; malformed/unknown tool requests fail closed; model/tool text cannot grant authority; no service credential is inserted into agent/model context; existing exact approval binding, pre-dispatch policy recheck, duplicate prevention, fail-closed behavior, environment isolation, filesystem containment, network containment, and child-process containment regressions remain green; no FreeToken/model-runtime capability is introduced by A001; Git is clean after tests.

**Package required?** yes.

**Next task on success:** `LAC-A002` — FreeToken model configuration, in a fresh implementation session.
