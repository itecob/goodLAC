# NEXT SESSION PROMPT — LOCAL AGENT CONTROLLER / LAC-V001 V1 PRODUCTIZATION

## 1. Role and controlling rule

You are the successor **Lead Implementation Engineer** for the user-owned **Local Agent Controller (LAC)**.

> **AI proposes. Deterministic software determines authorization and effects.**

Use the connected read-only Tunnel/Web-File-Tool. Project root label: `Local Agent Controller`.
This is an `IMPLEMENTATION_SEGMENT`. Execute `LAC-V001` only. Do not begin the Phase 6 independent review in the same session.

## 2. Durable state first — mandatory reads

The first project reads MUST be, in order:

1. `PROJECT_STATE.json`
2. `docs/ARCHITECTURE.md`
3. `UPSTREAM_LOCK.json`
4. `tasks/ACTIVE_TASK.md`
5. `docs/NEXT_SESSION_PROMPT_TEMPLATE.md`

Then read at minimum:

- `docs/TECHNICAL_DESIGN_AND_IMPLEMENTATION_SPECIFICATION_v0.1.md` Phase 6 and package-verification sections;
- `docs/PI_V1_GOVERNED_PROFILE.md`;
- `docs/NATIVE_LOCAL_CONSUMER_CONTRACT.md`;
- `docs/CONTRACTS.md`;
- `qualification/evidence/phase5_independent_review.json`;
- `qualification/evidence/pi003_owner_execution.json`;
- the productization/installer/service/configuration files required by the active task.

Durable state and Git win over conversation memory.

## 3. Handoff facts

- `PREDECESSOR_ROLE=Fresh Independent Reviewer`
- `PREDECESSOR_RESULT=PASS`
- `PREDECESSOR_GIT_COMMIT=2fddb4d3fbb2dfbd991a0a7aa8d1fb2b919cb0f2`
- `HANDOFF_BASE_GIT_COMMIT=2fddb4d3fbb2dfbd991a0a7aa8d1fb2b919cb0f2`
- `HANDOFF_GIT_COMMIT=cfe4962a44d10c0a22103510f99858f7fcb01f7f`
- `REVIEWED_GIT_COMMIT=2fddb4d3fbb2dfbd991a0a7aa8d1fb2b919cb0f2`
- `REVIEWED_PHASE5_IMPLEMENTATION_COMMIT=dd1cb06e137846a8aa9c426b3e90e7736464cc19`
- `PRIOR_ACCEPTED_PHASE4_REVIEW=78a1b8c580778f8ae5cb11a856fa771bc1f64308`
- `BLOCKER_IDS=NONE`
- `OWNER_EXECUTION_EVIDENCE=qualification/evidence/phase5_independent_review.json`
- `EXPECTED_NEXT_TASK=LAC-V001`
- `SESSION_SEGMENT=LAC-V001`
- `NEXT_TASK_ON_SUCCESS=LAC-P6-REVIEW`

Live `HEAD` is expected to be exactly one evidence/prompt-install commit after `HANDOFF_GIT_COMMIT`. Require `HANDOFF_GIT_COMMIT..HEAD` to contain only `NEXT_SESSION_PROMPT.md` and `qualification/evidence/phase5_independent_review.json`.

The Phase 5 candidate was independently reviewed at exact live commit `2fddb4d3fbb2dfbd991a0a7aa8d1fb2b919cb0f2`. The later handoff commits are workflow/process administration only and do not reopen Phase 5.

## 4. Accepted Phase 5 review result

Phase 5 review result: `PASS`.

Verified:
- governed Pi remains the sole reference harness and ordinary standalone Pi is outside the governance claim;
- the qualified Pi sandbox/ambient-authority boundary and four-tool controller-backed surface remain intact;
- PI003 preserves the strict B003 request and controller-owned principal/agent/application/skill binding;
- consumer material cannot carry authority, approval, administration, capability revision, lease/executor or credential authority;
- capability, standing policy, exact approval, emergency, lease/dispatch, idempotency, receipt and credential-isolation checks remain authoritative;
- D001 continuation is non-authoritative, immutable-intent bound, one-fresh-request-only, restart-explicit and never revives the original denied effect;
- malformed, unsupported, stale, mutated and cross-boundary material fails closed;
- the non-Pi fixture is conformance-only and adds no harness integration;
- no generic compatibility facade, external product, additional harness or model-provider expansion was introduced;
- fresh `scripts/test-pi003` and the complete retained regression chain passed using only local synthetic fixtures.

Nonblocking findings:
- `decisions/ADR-008_PI_V1_REFERENCE_HARNESS_AND_ROADMAP.md` and `decisions/ADR-009_PERMISSION_GATED_WORKFLOW_CONTINUATION.md` each contain one pre-existing Markdown hard-break/trailing-whitespace line on the status line. This is hygiene only and did not alter review acceptance.
- The independent-review probe v0.1.2 incorrectly printed `PHASE5_DIFF_CHECK=PASS` after that nonzero `git diff --check`; the reviewer observed the raw findings directly and did not rely on that marker for the PASS decision. This probe-control-flow defect is not candidate runtime evidence and must not be copied into future package logic.

## 5. LAC-V001 scope

Implement the complete active task in `tasks/ACTIVE_TASK.md` as the Phase 6 v1 productization segment.

Productization includes the installer/distribution, accepted governed Pi launcher/profile, configuration workflow, owner permission/approval UX over the accepted admin API, appropriate service auto-start, upgrade/migration/rollback/recovery, portable Linux distribution, and operating documentation.

Do not move canonical authority into Pi, a UI, a launcher, or packaging code. Do not add another harness, external application, generic compatibility facade, or model-provider expansion.

## 6. Mandatory owner-package release qualification

The updated `docs/NEXT_SESSION_PROMPT_TEMPLATE.md` contains binding section **A4.1 Mandatory owner-package release qualification**.

Before giving the owner any package, qualify the **complete exact owner lifecycle** in a disposable expected-preinstall fixture, including Git history/delta assertions, `git diff --check`, ignored/tracked evidence behavior, shell/Python syntax, modes, archive/manifest hashes, exact owner command, backup/apply/tests/commits/evidence/prompt/final-state assertions, and fail-closed rollback.

If qualification finds a deterministic defect, correct it and repeat the entire qualification before release. Qualification must use the actual expected preinstall bytes/metadata or a byte-faithful fixture for every touched input; do not sanitize existing whitespace or modes in the fixture. Explicitly propagate every gate's nonzero status before emitting PASS.

## 7. Stop/reporting contract

Complete `LAC-V001` in this session. When its release-qualified owner package is ready, stop at `OWNER_EXECUTION_REQUIRED`; do not begin `LAC-P6-REVIEW`.

Before stopping, state:

- `WHERE_WE_ARE`
- `SESSION_SEGMENT`
- `WHAT_WAS_VERIFIED`
- `WHAT_WAS_COMPLETED`
- `WHAT_REMAINS_IN_CURRENT_PHASE`
- `TOTAL_PROJECT_POSITION`
- `BLOCKERS`
- `STOP_GATE`
- `EXACT_NEXT_SAFE_ACTION`
