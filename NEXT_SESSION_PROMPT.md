# NEXT SESSION PROMPT — LOCAL AGENT CONTROLLER / PHASE 2 LAC-H004 BYPASS SUITE AND PHASE CANDIDATE

## 1. Purpose and authorized role

You are the **Lead Implementation Engineer** for the user-owned **Local Agent Controller (LAC)**.

Use the connected read-only Tunnel/Web-File-Tool. Project root label:

`Local Agent Controller`

This session owns exactly one implementation segment:

`SESSION_SEGMENT=LAC-H004`

The controlling rule remains:

> AI proposes. Deterministic software determines authorization and effects.

H001 established the selected Linux sandbox, H002 established the bounded typed filesystem effect path, and H003 established the typed shell effect path. Do not repeat those as new architecture exercises merely because the predecessor package advanced durable state.

Do not begin Phase 3 or `LAC-A001` in this conversation.

## 2. Mandatory first reads

Read exactly these first, in order:

1. `PROJECT_STATE.json`
2. `docs/ARCHITECTURE.md`
3. `UPSTREAM_LOCK.json`
4. `tasks/ACTIVE_TASK.md`
5. `docs/NEXT_SESSION_PROMPT_TEMPLATE.md`

Then read:

`docs/TECHNICAL_DESIGN_AND_IMPLEMENTATION_SPECIFICATION_v0.1.md`

Read only the additional H001/H002/H003 implementation/evidence/tests and Phase 1 authority material needed for `LAC-H004`.

Do not reconstruct project state from conversation memory.

## 3. Handoff facts

Preserve and boundedly verify:

* `PREDECESSOR_ROLE=Lead Implementation Engineer`
* `PREDECESSOR_RESULT=LAC-H003 PASS`
* `PREDECESSOR_GIT_COMMIT=c5879721a299c0cef21c0e6aee4349947a919ee4`
* `HANDOFF_BASE_GIT_COMMIT=c5879721a299c0cef21c0e6aee4349947a919ee4`
* `REVIEWED_GIT_COMMIT=ba21d50c26540147c458a8e3f402e15e71efe9c7`
* `REVIEW_PRESERVED_ACROSS_NONMATERIAL_DELTA=true`
* `BLOCKER_IDS=NONE`
* `OWNER_EXECUTION_EVIDENCE=${HOME}/Downloads/LAC_P2_H003_SHELL_ADAPTER_v0.1.0_20260913_123918.log`
* `EXPECTED_NEXT_TASK=LAC-H004`
* `SESSION_SEGMENT=LAC-H004`
* `H001_SELECTED_BACKEND=bubblewrap`
* `H001_QUALIFICATION_EVIDENCE=qualification/evidence/h001_sandbox.json`
* `H002_ADAPTER=filesystem:v1`
* `H002_TEST_GATE=scripts/test-h002`
* `H003_ADAPTER=shell:v1`
* `H003_TEST_GATE=scripts/test-h003`
* `LIVE_HANDOFF_GIT_COMMIT=READ_PROJECT_GIT_COMMIT_FROM_OWNER_EXECUTION_EVIDENCE_AND_REQUIRE_IT_TO_EQUAL_HEAD`

Exactly one handoff-only commit is expected after `PREDECESSOR_GIT_COMMIT`. Verify the complete `PREDECESSOR_GIT_COMMIT..HEAD` delta; the only permitted path is:

`NEXT_SESSION_PROMPT.md`

Any implementation, tests, architecture, qualification, policy, contracts, threat-model, dependency, license, acceptance-criteria, or other H003 substance change after the H003 implementation commit is a discrepancy to classify under template v0.2.0 before proceeding.

Do not reopen Phase 0 or repeat the Phase 1 formal independent review when this handoff verifies correctly.

## 4. Session mode

Use:

`MODE A — IMPLEMENTATION_SEGMENT`

Role:

`Lead Implementation Engineer`

Perform bounded predecessor verification and then implement `LAC-H004` completely in this session.

## 5. Active segment — LAC-H004

### Objective

Complete the Phase 2 local-host-enforcement bypass/adversarial suite against the accepted H001 sandbox, H002 filesystem adapter, and H003 shell adapter. Correct only concrete in-scope defects exposed by the suite, then prepare the Phase 2 candidate for fresh independent review.

### Required adversarial effects

Challenge the complete binding Phase 2 set as actual effects, including:

* `../` path traversal;
* symlink escape;
* read `~/.ssh`;
* read `.env` outside the workspace;
* write outside the workspace;
* denied file deletion;
* unauthorized binary execution;
* launch a shell through an otherwise allowed command;
* interpreter-based command restriction escape;
* network access through subprocesses;
* inherited secret environment variables;
* child process attempting to outlive the sandbox.

The test criterion is not that policy returned `DENY`; it is whether the forbidden effect could actually occur.

### Scope discipline

Do not implement Pi, FreeToken, credentials, external-service effects, Phase 3, or unrelated productization. Do not broaden H004 beyond the Phase 2 bypass/conformance boundary and narrow remediation required by concrete failed tests.

## 6. Binding requirements

Preserve all controller invariants, especially `INV-003`, `INV-004`, `INV-005`, `INV-006`, `INV-008`, `INV-010`, and `INV-014`.

The H001 `network=none` and cleared-environment contracts remain binding. H002 workspace containment and H003 exact executable/argv/cwd/environment binding remain binding.

## 7. Required validation

Before handoff:

1. run the complete H004 actual-effect adversarial suite;
2. correct every concrete in-scope Phase 2 defect found;
3. rerun affected tests and the complete H004 gate;
4. run `scripts/test-h003`;
5. run `scripts/test-h002`;
6. run `scripts/test-h001`;
7. run the complete applicable Phase 1 regression gate;
8. verify no Phase 3 capability was introduced;
9. prepare a Phase 2 candidate for exactly one fresh independent review.

Do not hand known Phase 2 defects to the reviewer.

## 8. Owner-executable package

When local mutation is required, produce one meaningful H004 package following template v0.2.0. Its successful execution must leave Git/state/task/prompt mutually consistent for a fresh `PHASE_BOUNDARY_INDEPENDENT_REVIEW` of the Phase 2 candidate, not for Phase 3 implementation.

The package must fail closed on unexpected Git/state/task input, preserve the terminal, emit explicit PASS/FAIL, and record durable owner execution evidence.

## 9. Stop rule

This fresh session owns only `LAC-H004`.

When the H004 package is ready, stop at:

`OWNER_EXECUTION_REQUIRED`

Do not perform the independent review in the implementation conversation. After successful owner execution, a fresh independent-review session owns the Phase 2 candidate.

## 10. Required stop status

Before stopping, report:

* `WHERE_WE_ARE`
* `SESSION_SEGMENT=LAC-H004`
* `PREDECESSOR_GIT_COMMIT=c5879721a299c0cef21c0e6aee4349947a919ee4`
* `H001_SELECTED_BACKEND=bubblewrap`
* `H002_ADAPTER=filesystem:v1`
* `H003_ADAPTER=shell:v1`
* `WHAT_WAS_VERIFIED`
* `WHAT_WAS_COMPLETED`
* `WHAT_REMAINS_IN_CURRENT_PHASE`
* `TOTAL_PROJECT_POSITION`
* `BLOCKERS`
* `STOP_GATE`
* `EXACT_NEXT_SAFE_ACTION`

Keep evidence separate from conclusions.

Do not broaden the project.
