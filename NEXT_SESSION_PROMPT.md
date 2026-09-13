# NEXT SESSION PROMPT — LOCAL AGENT CONTROLLER / PHASE 2 FRESH INDEPENDENT REVIEW

## 1. Purpose, authorized role, and Secure-SDLC scope

You are the **Fresh Independent Reviewer** for the user-owned **Local Agent Controller (LAC)**.

Use the connected read-only Tunnel/Web-File-Tool. Project root label:

`Local Agent Controller`

This session owns exactly:

`SESSION_SEGMENT=LAC-P2-REVIEW`

The controlling rule remains:

> AI proposes. Deterministic software determines authorization and effects.

This is defensive Secure-SDLC work on software owned and operated by the project owner. Security validation is limited to source inspection and deterministic tests using the LAC repository, temporary local workspaces, synthetic files/canary values, local test databases, isolated local sandbox instances, and other non-production fixtures. Do not use real credentials, production accounts, third-party systems, external targets, or generalized procedures for circumventing security controls.

Do not remediate implementation in this conversation. Do not begin Phase 3 or `LAC-A001` unless this independent review first returns `PASS`; even on PASS, provide the successor prompt and stop rather than implementing A001 here.

## 2. Mandatory first reads

Read exactly these first, in order:

1. `PROJECT_STATE.json`
2. `docs/ARCHITECTURE.md`
3. `UPSTREAM_LOCK.json`
4. `tasks/ACTIVE_TASK.md`
5. `docs/NEXT_SESSION_PROMPT_TEMPLATE.md`

Then read:

`docs/TECHNICAL_DESIGN_AND_IMPLEMENTATION_SPECIFICATION_v0.1.md`

Read only the additional Phase 1 authority and H001/H002/H003/H004 implementation/evidence/tests needed to review Phase 2.

Do not reconstruct project state from conversation memory.

## 3. Handoff facts and process-only delta

Preserve and independently verify:

* `PREDECESSOR_ROLE=Lead Implementation Engineer`
* `PREDECESSOR_RESULT=LAC-H004 PASS`
* `PREDECESSOR_GIT_COMMIT=5cdd824b083ede92c192ef17f039cdbf0206cc44`
* `HANDOFF_BASE_GIT_COMMIT=5cdd824b083ede92c192ef17f039cdbf0206cc44`
* `REVIEWED_GIT_COMMIT=NONE_FOR_PHASE_2`
* `PHASE1_REVIEWED_GIT_COMMIT=ba21d50c26540147c458a8e3f402e15e71efe9c7`
* `BLOCKER_IDS=NONE`
* `OWNER_EXECUTION_EVIDENCE=${HOME}/Downloads/LAC_P2_H004_BYPASS_SUITE_v0.1.1_20260913_113423.log`
* `EXPECTED_NEXT_TASK=LAC-P2-REVIEW`
* `SESSION_SEGMENT=LAC-P2-REVIEW`
* `H001_SELECTED_BACKEND=bubblewrap`
* `H001_QUALIFICATION_EVIDENCE=qualification/evidence/h001_sandbox.json`
* `H002_ADAPTER=filesystem:v1`
* `H002_TEST_GATE=scripts/test-h002`
* `H003_ADAPTER=shell:v1`
* `H003_TEST_GATE=scripts/test-h003`
* `H004_TEST_GATE=scripts/test-h004`
* `LIVE_HANDOFF_GIT_COMMIT=READ_LIVE_HEAD_AND_REQUIRE_OWNER_PROCESS_UPDATE_EVIDENCE_TO_MATCH`

The Phase 2 implementation candidate remains exactly `5cdd824b083ede92c192ef17f039cdbf0206cc44`.

Two post-candidate workflow commits are expected:

1. `77cd0415aacf5566154d771c634460291e9fe850` — original Phase 2 review handoff; only `NEXT_SESSION_PROMPT.md` changed.
2. the current `HEAD` — process-only Secure-SDLC framing update; only these paths may differ from `77cd0415aacf5566154d771c634460291e9fe850`:
   * `NEXT_SESSION_PROMPT.md`
   * `docs/NEXT_SESSION_PROMPT_TEMPLATE.md`
   * `tasks/ACTIVE_TASK.md`

The current process commit must have subject:

`workflow: clarify secure-sdlc review framing`

Verify the complete `PREDECESSOR_GIT_COMMIT..HEAD` delta. Any implementation, tests, architecture, qualification, policy, contracts, threat-model, dependency, license, acceptance-criteria substance, or other Phase 2 candidate change after the implementation commit is a discrepancy to classify before trusting the candidate. The permitted workflow edits above are non-material wording/process changes and must not alter the security acceptance semantics.

## 4. Session mode

Use exactly:

`MODE B — PHASE_BOUNDARY_INDEPENDENT_REVIEW`

Role:

`Fresh Independent Reviewer`

This is the one formal independent review for the Phase 2 candidate. Do not mutate the implementation.

## 5. Binding review target and negative security conformance

Review the complete Phase 2 candidate against the controlling specification, with particular attention to `INV-003`, `INV-004`, `INV-005`, `INV-006`, `INV-008`, `INV-010`, and `INV-014`.

Treat the specification's historical adversarial terminology as **negative security conformance testing**. The required assertions are:

* workspace path containment, including parent-reference rejection;
* symlink containment across read and write paths;
* host-only sensitive fixtures remain inaccessible to the governed process;
* writes remain confined to the configured workspace;
* policy-denied deletion preserves the target file;
* only reviewed executable identities can be selected;
* generic command-launching executables cannot become a `shell:v1` execution route through runtime/user configuration;
* interpreter/runtime executables cannot become a generic `shell:v1` execution route through runtime/user configuration;
* subprocesses have no outbound network authority under the selected sandbox profile;
* host secret-bearing environment state is not inherited by governed processes;
* child processes cannot persist beyond the sandbox lifecycle;
* explicitly allowed bounded workspace effects remain functional.

For operating-system containment properties, a policy result such as `DENY` is not sufficient evidence by itself. The deterministic test must establish that the prohibited effect did not occur.

Do not develop generalized circumvention procedures or reusable techniques for defeating security controls. If existing evidence is insufficient, use or recommend the smallest synthetic deterministic regression test needed to establish the documented invariant.

## 6. Required validation

At minimum:

1. verify candidate Git identity, clean state, and both workflow-only deltas described above;
2. inspect H001 qualification evidence and live selected-backend contract;
3. inspect H002 filesystem containment and deletion semantics;
4. inspect H003 exact executable/argv/cwd/environment binding;
5. inspect the H004 remediation and every required negative actual-effect conformance test;
6. run `scripts/test-h004`;
7. run `scripts/test-h003`;
8. run `scripts/test-h002`;
9. run `scripts/test-h001`;
10. run the complete applicable Phase 1 regression gate;
11. use bounded synthetic deterministic tests only where existing evidence is insufficient to establish a binding claim;
12. verify no Phase 3 capability was introduced.

Separate evidence from conclusions. Predecessor PASS claims are not evidence by themselves.

## 7. Finding discipline

A finding is `BLOCKER` only when it demonstrates a concrete violation of a binding invariant, acceptance criterion, security boundary, package/data integrity, credential isolation, required functionality, reproducibility, or material control-boundary failure.

Everything else is `NONBLOCKING` and does not prevent progression.

Do not redesign the project during review.

## 8. Verdict and successor rule

Return exactly one formal verdict:

`PASS`

or

`BLOCKED`

If `PASS`, Phase 2 may advance to a fresh `LAC-A001` Phase 3 implementation session. Produce the complete populated successor `NEXT_SESSION_PROMPT.md` for `LAC-A001`, preserving the exact reviewed Phase 2 implementation commit identity. Do not implement A001 in this review conversation.

If `BLOCKED`, assign blocker IDs and produce a complete fresh remediation-segment prompt limited to those blockers. The remediator must rerun affected tests plus the full Phase 2 gate and return a corrected candidate to one fresh re-review.

## 9. Required stop status

Before stopping, report:

* `WHERE_WE_ARE`
* `SESSION_SEGMENT=LAC-P2-REVIEW`
* `REVIEWED_PHASE2_GIT_COMMIT`
* `WHAT_WAS_VERIFIED`
* `FORMAL_VERDICT`
* `BLOCKERS`
* `NONBLOCKING_FINDINGS`
* `WHAT_REMAINS_IN_CURRENT_PHASE`
* `TOTAL_PROJECT_POSITION`
* `STOP_GATE`
* `EXACT_NEXT_SAFE_ACTION`

Keep evidence separate from conclusions.

Do not broaden the project.
