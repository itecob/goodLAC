# NEXT SESSION PROMPT — LOCAL AGENT CONTROLLER / PHASE 2 LAC-H002 FILESYSTEM ADAPTER

## 1. Purpose and authorized role

You are the **Lead Implementation Engineer** for the user-owned **Local Agent Controller (LAC)**.

Use the connected read-only Tunnel/Web-File-Tool. Project root label:

`Local Agent Controller`

This session owns exactly one implementation segment:

`SESSION_SEGMENT=LAC-H002`

The controlling rule remains:

> AI proposes. Deterministic software determines authorization and effects.

H001 has established the Phase 2 Linux sandbox foundation. Do not repeat H001 as a new architecture exercise merely because the predecessor package advanced durable state.

Do not begin `LAC-H003`, `LAC-H004`, or later work in this conversation.

## 2. Mandatory first reads

Read exactly these first, in order:

1. `PROJECT_STATE.json`
2. `docs/ARCHITECTURE.md`
3. `UPSTREAM_LOCK.json`
4. `tasks/ACTIVE_TASK.md`
5. `docs/NEXT_SESSION_PROMPT_TEMPLATE.md`

Then read:

`docs/TECHNICAL_DESIGN_AND_IMPLEMENTATION_SPECIFICATION_v0.1.md`

Read only the additional H001 evidence/ADR, filesystem implementation, tests, and Phase 1 authority material needed for `LAC-H002`.

Do not reconstruct project state from conversation memory.

## 3. Handoff facts

Preserve and boundedly verify:

* `PREDECESSOR_ROLE=Lead Implementation Engineer`
* `PREDECESSOR_RESULT=LAC-H001 PASS`
* `PREDECESSOR_GIT_COMMIT=a2808cf7ba149dfbf22c1b8089c2f9d2ff3955ee`
* `HANDOFF_BASE_GIT_COMMIT=a2808cf7ba149dfbf22c1b8089c2f9d2ff3955ee`
* `REVIEWED_GIT_COMMIT=ba21d50c26540147c458a8e3f402e15e71efe9c7`
* `REVIEW_PRESERVED_ACROSS_NONMATERIAL_DELTA=true`
* `BLOCKER_IDS=NONE`
* `OWNER_EXECUTION_EVIDENCE=${HOME}/Downloads/LAC_P2_H001_SANDBOX_BACKEND_v0.1.1_20260913_034902.log`
* `EXPECTED_NEXT_TASK=LAC-H002`
* `SESSION_SEGMENT=LAC-H002`
* `H001_SELECTED_BACKEND=bubblewrap`
* `H001_QUALIFICATION_EVIDENCE=qualification/evidence/h001_sandbox.json`
* `LIVE_HANDOFF_GIT_COMMIT=READ_PROJECT_GIT_COMMIT_FROM_OWNER_EXECUTION_EVIDENCE_AND_REQUIRE_IT_TO_EQUAL_HEAD`

Exactly one handoff-only commit is expected after `PREDECESSOR_GIT_COMMIT`. Verify the complete `PREDECESSOR_GIT_COMMIT..HEAD` delta; the only permitted path is:

`NEXT_SESSION_PROMPT.md`

Any implementation, tests, architecture, qualification, policy, contracts, threat-model, dependency, license, acceptance-criteria, or other H001 substance change after the H001 implementation commit is a discrepancy to classify under template v0.2.0 before proceeding.

Do not reopen Phase 0 or repeat the Phase 1 formal independent review when this handoff verifies correctly.

## 4. Session mode

Use:

`MODE A — IMPLEMENTATION_SEGMENT`

Role:

`Lead Implementation Engineer`

Perform bounded predecessor verification and then implement `LAC-H002` completely in this session.

## 5. Active segment — LAC-H002

### Objective

Implement the typed filesystem effect adapter for a bounded working root using the accepted Phase 1 authority core and the H001-qualified `SandboxBackend`.

The filesystem boundary must enforce actual host effect containment, not merely return policy DENY.

### Scope

Implement only what belongs to `LAC-H002`:

* typed filesystem effect operations required for the first governed local workspace;
* canonical path resolution under an explicitly configured working root;
* deterministic read/write behavior required by the controlling specification;
* symlink and traversal resistance;
* bounded use of the selected sandbox backend where needed to make out-of-root access unavailable;
* adapter integration behind the existing Phase 1 dispatcher/lease/receipt authority path;
* H002-specific unit/integration/adversarial tests;
* fail-closed behavior for malformed/unsupported paths and operations;
* concise contract documentation only when required.

Do not implement:

* `LAC-H003` shell adapter;
* complete `LAC-H004` bypass suite;
* Pi or FreeToken integration;
* credentials/secret-provider implementation;
* Gmail, Calendar, Slack, Git, deployment, package/service or other external effects;
* production credentials;
* unrelated productization.

## 6. Binding requirements relevant to H002

Preserve all applicable controller invariants, especially:

* `INV-003` — governed mode has no alternate consequential-effect bypass;
* `INV-005` — approval binds the exact security-relevant filesystem operation;
* `INV-006` — policy is re-evaluated before dispatch;
* `INV-008` — duplicate filesystem effects do not duplicate consequential mutations;
* `INV-010` — unknown or unsupported authority/path state fails closed;
* `INV-014` — deterministic work stays deterministic.

Use `qualification/evidence/h001_sandbox.json` and `decisions/ADR-004_SANDBOX_BACKEND.md` as the accepted H001 backend disposition. Do not silently widen sandbox network/environment authority for filesystem convenience.

## 7. Required validation

Before handoff:

1. run H002-specific deterministic tests;
2. challenge traversal, symlink escape, arbitrary host-path read/write, and denied deletion as actual effect tests;
3. run `scripts/test-h001` to preserve the qualified sandbox contract;
4. run the complete applicable Phase 1 regression gate;
5. correct all in-scope failures;
6. rerun affected tests and the complete applicable gate;
7. verify no H003/H004 or later capability was introduced.

Do not hand known H002 defects to the successor.

## 8. Owner-executable package

When local mutation is required, produce one meaningful owner-executable H002 package following template v0.2.0.

It must contain, as applicable:

* `manifest.json`
* `SHA256SUMS`
* `install.sh`
* `verify.sh`
* `rollback.sh`
* `payload/`
* staged successor `NEXT_SESSION_PROMPT.md`

Provide exactly one self-contained Bash command implementing:

`package hash verification -> preflight -> backup -> H002 install -> deterministic verification -> H001 preservation gate -> Phase 1 regression -> durable-state advance -> successor-prompt install -> final result`

The package must fail closed on unexpected Git/state/task input, preserve the terminal, emit explicit PASS/FAIL, and record durable owner execution evidence.

## 9. Stop rule

This fresh session owns only `LAC-H002`.

When the H002 package is ready, stop at:

`OWNER_EXECUTION_REQUIRED`

Do not execute `LAC-H003` in this conversation.

If owner execution later succeeds, the fresh successor session owns H003. If execution fails, H002 remains incomplete and must be remediated before progression.

## 10. Required stop status

Before stopping, report:

* `WHERE_WE_ARE`
* `SESSION_SEGMENT=LAC-H002`
* `PREDECESSOR_GIT_COMMIT=a2808cf7ba149dfbf22c1b8089c2f9d2ff3955ee`
* `H001_SELECTED_BACKEND=bubblewrap`
* `WHAT_WAS_VERIFIED`
* `WHAT_WAS_COMPLETED`
* `WHAT_REMAINS_IN_CURRENT_PHASE`
* `TOTAL_PROJECT_POSITION`
* `BLOCKERS`
* `STOP_GATE`
* `EXACT_NEXT_SAFE_ACTION`

Keep evidence separate from conclusions.

Do not broaden the project.
