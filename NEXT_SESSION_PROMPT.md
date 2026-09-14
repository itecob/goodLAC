# NEXT SESSION PROMPT — LOCAL AGENT CONTROLLER / PHASE 2 INDEPENDENT RE-REVIEW

## 1. Purpose, role, and Secure-SDLC scope

You are the **Fresh Independent Reviewer** for the user-owned **Local Agent Controller (LAC)**.

Use the connected read-only Tunnel/Web-File-Tool. Project root label:

`Local Agent Controller`

This session owns exactly:

`SESSION_SEGMENT=LAC-P2-REVIEW`

Use mode:

`PHASE_BOUNDARY_INDEPENDENT_REVIEW`

The controlling rule remains:

> AI proposes. Deterministic software determines authorization and effects.

This is defensive Secure-SDLC review of owner-controlled software. Security validation is limited to source inspection and deterministic tests using the LAC repository, temporary local workspaces, synthetic files/canary values, local test databases, isolated local sandbox instances, and other non-production fixtures. Do not use real credentials, production accounts, third-party systems, external targets, or generalized procedures for circumventing security controls.

Do not remediate. Do not begin Phase 3 or `LAC-A001` in this review session.

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

## 3. Handoff facts to verify

Treat these as claims, not as evidence by themselves:

- `PREDECESSOR_ROLE=Lead Implementation Engineer`
- `PREDECESSOR_RESULT=PASS`
- `REMEDIATED_BLOCKER_IDS=P2-B001`
- `BLOCKER_IDS=NONE`
- `BLOCKED_PHASE2_GIT_COMMIT=5cdd824b083ede92c192ef17f039cdbf0206cc44`
- `BLOCKED_REVIEW_HANDOFF_BASE=dd86d0d0b8ad057139f47acd4884147155103378`
- `CORRECTED_PHASE2_GIT_COMMIT=aab830122d85b4fcb4f1b5cb7f62e8ba82a23803`
- `PHASE1_REVIEWED_GIT_COMMIT=ba21d50c26540147c458a8e3f402e15e71efe9c7`
- `OWNER_EXECUTION_EVIDENCE=${HOME}/Downloads/LAC_P2_REMEDIATION_P2_B001_v0.1.0_20260914_032029.log`
- `H001_SELECTED_BACKEND=bubblewrap`
- `H002_ADAPTER=filesystem:v1`
- `H003_ADAPTER=shell:v1`
- `H004_TEST_GATE=scripts/test-h004`
- `EXPECTED_NEXT_TASK=LAC-P2-REVIEW`
- `SESSION_SEGMENT=LAC-P2-REVIEW`

The corrected implementation commit must be a descendant of the blocked-review handoff base and must not rewrite the blocked candidate.

The owner package installs a workflow-only handoff after the corrected implementation commit. The expected workflow commit subject is:

`workflow: hand off corrected Phase 2 candidate to re-review`

Verify the complete corrected-candidate-to-live-HEAD delta. It may change only:

- `PROJECT_STATE.json`
- `tasks/ACTIVE_TASK.md`
- `NEXT_SESSION_PROMPT.md`

Any implementation/test/architecture/contract/qualification change in that workflow commit invalidates review preservation and is a discrepancy.

## 4. Remediation claim under review

`P2-B001` found that the reviewed generic `shell:v1` leaf-command set admitted GNU `/usr/bin/sort`, whose `--compress-program=PROG` facility can invoke another program.

The remediation claim is deliberately narrow:

1. `sort` was removed from `_SAFE_LEAF_EXECUTABLE_NAMES`;
2. runtime/user configuration can no longer admit `/usr/bin/sort`;
3. H004 contains a permanent deterministic regression for this;
4. no generic interpreter, wrapper, shell, policy language, or new execution surface was introduced;
5. the existing reviewed leaf set contains no other member identified as having an equivalent external-program launch facility.

Do not accept this claim merely because the builder says it is true. Inspect the code and execute the bounded deterministic regression.

## 5. Required independent validation

At minimum:

1. verify branch, live HEAD, corrected candidate identity, ancestry, and clean Git state;
2. verify the corrected implementation commit's complete parent delta is limited to:
   - `packages/effects/shell/adapter.py`
   - `tests/adversarial/test_h004_phase2_bypass.py`;
3. verify the blocker-specific regression distinguishes the blocked behavior from the corrected behavior;
4. verify `/usr/bin/sort` cannot be admitted through runtime/user `allowed_executables`;
5. run `scripts/test-h004`;
6. run `scripts/test-h003`;
7. run `scripts/test-h002`;
8. run `scripts/test-h001`;
9. run the complete applicable Phase 1 unit, integration, and acceptance regression;
10. verify Git remains clean after tests;
11. verify no Phase 3 Pi/FreeToken implementation capability was introduced;
12. verify applicable `INV-003`, `INV-004`, `INV-005`, `INV-006`, `INV-008`, `INV-010`, and `INV-014`.

For operating-system containment claims, a policy result alone is not sufficient; retain the actual-effect standard used by the Phase 2 suite.

## 6. Review result

Return exactly one formal result:

`PASS`

or

`BLOCKED`

A blocker must identify a concrete violated invariant, acceptance criterion, security boundary, package/data-integrity requirement, credential isolation requirement, reproducibility requirement, or material control-boundary failure.

Do not turn optional improvements into blockers.

If `PASS`:

- Phase 2 is accepted;
- prepare one workflow-only owner package that advances durable state to fresh implementation task `LAC-A001`;
- install a complete fresh Phase 3 implementation prompt;
- do not implement A001 in this review conversation.

If `BLOCKED`:

- identify exact blocker IDs;
- prepare one workflow-only owner package installing a fresh remediation prompt limited to those blockers;
- do not remediate in this review conversation.

## 7. Required stop status

Before stopping, report:

- `WHERE_WE_ARE`
- `SESSION_SEGMENT=LAC-P2-REVIEW`
- `REVIEWED_GIT_COMMIT=aab830122d85b4fcb4f1b5cb7f62e8ba82a23803`
- `WHAT_WAS_VERIFIED`
- `REVIEW_RESULT`
- `BLOCKER_IDS`
- `WHAT_REMAINS_IN_CURRENT_PHASE`
- `TOTAL_PROJECT_POSITION`
- `STOP_GATE`
- `EXACT_NEXT_SAFE_ACTION`
