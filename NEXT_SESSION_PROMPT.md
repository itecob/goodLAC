# NEXT SESSION PROMPT — LOCAL AGENT CONTROLLER / PHASE 2 BLOCKER REMEDIATION P2-B001

## 1. Purpose, authorized role, and Secure-SDLC scope

You are the **Lead Implementation Engineer** for the user-owned **Local Agent Controller (LAC)**.

Use the connected read-only Tunnel/Web-File-Tool. Project root label:

`Local Agent Controller`

This session owns exactly:

`SESSION_SEGMENT=LAC-P2-REMEDIATION-P2-B001`

The controlling rule remains:

> AI proposes. Deterministic software determines authorization and effects.

This is defensive Secure-SDLC work on software owned and operated by the project owner. Security validation is limited to source inspection and deterministic tests using the LAC repository, temporary local workspaces, synthetic files/canary values, local test databases, isolated local sandbox instances, and other non-production fixtures. Do not use real credentials, production accounts, third-party systems, external targets, or generalized procedures for circumventing security controls.

Remediate **only** blocker `P2-B001`. Do not redesign the project. Do not begin Phase 3 or `LAC-A001`. After remediation, return the corrected Phase 2 candidate to one fresh independent re-review.

## 2. Mandatory first reads

Read exactly these first, in order:

1. `PROJECT_STATE.json`
2. `docs/ARCHITECTURE.md`
3. `UPSTREAM_LOCK.json`
4. `tasks/ACTIVE_TASK.md`
5. `docs/NEXT_SESSION_PROMPT_TEMPLATE.md`

Then read:

- `docs/TECHNICAL_DESIGN_AND_IMPLEMENTATION_SPECIFICATION_v0.1.md`
- `docs/CONTRACTS.md`
- `packages/effects/shell/adapter.py`
- `tests/unit/test_shell_adapter.py`
- `tests/integration/test_shell_dispatch.py`
- `tests/adversarial/test_h003_shell_boundary.py`
- `tests/adversarial/test_h004_phase2_bypass.py`
- `scripts/test-h004`
- `scripts/test-h003`
- `scripts/test-h002`
- `scripts/test-h001`

Read only additional Phase 1 authority files/tests necessary for the regression gate.

Do not reconstruct project state from conversation memory.

## 3. Verified predecessor facts

Preserve and independently verify:

- `PREDECESSOR_ROLE=Fresh Independent Reviewer`
- `PREDECESSOR_RESULT=BLOCKED`
- `BLOCKER_IDS=P2-B001`
- `REVIEWED_PHASE2_GIT_COMMIT=5cdd824b083ede92c192ef17f039cdbf0206cc44`
- `PHASE1_REVIEWED_GIT_COMMIT=ba21d50c26540147c458a8e3f402e15e71efe9c7`
- `BLOCKED_REVIEW_LIVE_HEAD=e91773530125ebcd01a441d83b6bc91018864325`
- `HANDOFF_BASE_GIT_COMMIT=e91773530125ebcd01a441d83b6bc91018864325`
- `OWNER_EXECUTION_EVIDENCE=${HOME}/Downloads/LAC_P2_INDEPENDENT_REVIEW_EVIDENCE_20260913_223217.log`
- `H001_SELECTED_BACKEND=bubblewrap`
- `H002_ADAPTER=filesystem:v1`
- `H003_ADAPTER=shell:v1`
- `H004_TEST_GATE=scripts/test-h004`
- `EXPECTED_NEXT_TASK=LAC-P2-REMEDIATION-P2-B001`
- `SESSION_SEGMENT=LAC-P2-REMEDIATION-P2-B001`

The blocked Phase 2 implementation candidate is exactly:

`5cdd824b083ede92c192ef17f039cdbf0206cc44`

The independent review verified:

- live branch `main`;
- review-time live HEAD `e91773530125ebcd01a441d83b6bc91018864325`;
- clean Git state before and after tests;
- candidate -> original review handoff changed only `NEXT_SESSION_PROMPT.md`;
- original review handoff -> review-time live HEAD changed only `NEXT_SESSION_PROMPT.md`, `docs/NEXT_SESSION_PROMPT_TEMPLATE.md`, and `tasks/ACTIVE_TASK.md`;
- `scripts/test-h004` PASS;
- `scripts/test-h003` PASS;
- `scripts/test-h002` PASS;
- `scripts/test-h001` PASS;
- complete applicable Phase 1 unit, integration, and acceptance regressions PASS;
- no Phase 3 Pi/FreeToken implementation files were present under `packages`.

The workflow package that installed this prompt is expected to have a commit whose subject is:

`workflow: hand off Phase 2 blocker P2-B001 remediation`

Treat that commit as a non-material blocked-review handoff only. Verify its complete parent-to-HEAD delta before trusting it. It may change only:

- `PROJECT_STATE.json`
- `tasks/ACTIVE_TASK.md`
- `NEXT_SESSION_PROMPT.md`

Any implementation/test/architecture/contract/qualification change in that workflow commit is a discrepancy.

## 4. Formal blocker

### `P2-B001 — shell:v1 executable-class closure admits GNU sort, which can invoke another program`

The Phase 2 contract requires runtime/user executable configuration to be narrowing-only and says generic command-launching executables cannot become a `shell:v1` route.

The reviewed implementation includes `sort` in `_SAFE_LEAF_EXECUTABLE_NAMES`.

The live review probe established:

- `/usr/bin/sort` exists;
- `/usr/bin/sort --help` exposes `--compress-program=PROG`;
- `ShellEffectAdapter(... allowed_executables=(Path("/usr/bin/sort"),))` accepts it;
- the adapter reports `/usr/bin/sort` as an allowed executable.

GNU `sort` uses `--compress-program=PROG` to invoke the specified program for temporary-file processing. Therefore the reviewed "non-launching" set contains an executable with an external-program launch facility.

The existing green H004/H003 tests demonstrate a coverage gap; they do not negate this finding.

## 5. Required remediation

Use the smallest conservative remediation.

At minimum:

1. make `/usr/bin/sort` ineligible for generic `shell:v1`;
2. add a permanent deterministic regression proving runtime/user configuration cannot admit it;
3. inspect the existing `_SAFE_LEAF_EXECUTABLE_NAMES` set only as necessary to ensure no other member exposes an equivalent external-program execution facility that contradicts the documented non-launching classification;
4. if such an equivalent member is found, remove it and add the smallest corresponding regression;
5. do not add a generic interpreter, wrapper, shell, executable policy language, or new execution surface;
6. do not weaken the contract or convert this into documentation-only remediation.

## 6. Required validation

After remediation:

1. prove the blocker-specific regression distinguishes the pre-remediation behavior from corrected behavior;
2. run `scripts/test-h004`;
3. run `scripts/test-h003`;
4. run `scripts/test-h002`;
5. run `scripts/test-h001`;
6. run the complete applicable Phase 1 regression gate;
7. verify Git is clean after tests;
8. verify no Phase 3 capability was introduced;
9. preserve `INV-003`, `INV-004`, `INV-005`, `INV-006`, `INV-008`, `INV-010`, and `INV-014` as applicable.

## 7. Package and durable handoff

Local mutation is required. Produce one owner-executable remediation package containing, as applicable:

- `manifest.json`
- `SHA256SUMS`
- `install.sh`
- `verify.sh`
- `rollback.sh`
- `payload/`
- staged successor `NEXT_SESSION_PROMPT.md`

Provide exactly one self-contained Bash command implementing:

`package hash verification -> preflight -> backup -> install -> deterministic verification -> durable-state advance -> successor-prompt install -> final result`

The package must fail closed on unexpected Git/state/task input, create a new corrected Phase 2 implementation commit rather than rewriting the blocked candidate, record execution evidence in Downloads, and install a fresh Phase 2 **independent re-review** prompt before reporting PASS.

After successful owner execution, the project remains in Phase 2 candidate/re-review state. Do not advance to Phase 3 until that fresh re-review returns `PASS`.

## 8. Required stop status

Before stopping, report:

- `WHERE_WE_ARE`
- `SESSION_SEGMENT=LAC-P2-REMEDIATION-P2-B001`
- `WHAT_WAS_VERIFIED`
- `WHAT_WAS_COMPLETED`
- `CORRECTED_PHASE2_GIT_COMMIT`
- `BLOCKER_IDS`
- `BLOCKER_REMEDIATION_STATUS`
- `WHAT_REMAINS_IN_CURRENT_PHASE`
- `TOTAL_PROJECT_POSITION`
- `STOP_GATE`
- `EXACT_NEXT_SAFE_ACTION`

The implementation session stops at `OWNER_EXECUTION_REQUIRED` when the remediation package is ready. It must not continue into the independent re-review or Phase 3 in the same conversation.
